import logging
import os
import sys
import time
from collections import namedtuple
from logging     import handlers

import pyfgc
import program_manager.regfgc3_programmer as programmer


class ProgrammingSummary:
    def __init__(self):
        self.to_pb_fail  = 0
        self.to_db_fail  = 0
        self.reprog_fail = 0
        self.reprog_1st  = 0
        self.reprog_2nd  = 0
        self.reprog_3ed  = 0

    def __str__(self):
        return f"""to production boot failures: {self.to_pb_fail};
            to download boot failures: {self.to_db_fail};
            reprog success_1st: {self.reprog_1st};
            reprog success_2nd: {self.reprog_2nd};
            reprog success_3ed: {self.reprog_3ed}"""

# Constants
PROGRAMMING_DATA_DIR = os.path.join(
                        os.path.expanduser("~"),
                          "work",
                          "projects",
                          "fgc",
                          "sw",
                          "clients",
                          "python",
                          "program_manager",
                          "data"
                        )
                        
PROGRAMMING_DATA_FILE = os.path.join(PROGRAMMING_DATA_DIR, "prog_data.csv")

# Globals
_module_logger = None

try:
    tasks

except NameError:
    tasks = list()

try:
    tasks_per_converter_and_slot

except NameError:
    tasks_per_converter_and_slot = dict()

try:
    prog_summary

except NameError:
    prog_summary = dict()


# Functions
# def _is_board_in_download_boot(converter, slot):
#     global _module_logger
#     slot_info = ""

#     try:
#         r = pyfgc.get(converter, "REGFGC3.SLOT_INFO")
#         slot_info = r.value

#     except pyfgc.FgcResponseError:
#         _module_logger.error(f"{r.err_code}: {r.err_msg}")
#         sys.exit(2)

#     except RuntimeError as re:
#         _module_logger.error(re)
#         sys.exit(2)

#     while not slot_info.startswith("-"):
#         time.sleep(2)
#         slot_info = pyfgc.get(converter, "REGFGC3.SLOT_INFO").value

#     boards = programmer.parse_slot_info(slot_info)
#     try:
#         boards[slot]

#     except KeyError:
#         raise KeyError(f"Board not found in slot {slot}")

#     print(f"data for board in slot {slot}: {boards[slot]}")
#     if not programmer.is_board_in_download_boot(boards[slot]):
#         return False
    
#     else:
#         return True

# def switch_board_to_download_boot(converter, slot, board):
#     attempts = 3
    
#     if _is_board_in_download_boot(converter, slot):
#         global _module_logger
#         _module_logger.info(f"Target: board {board} in {converter} already in download boot. Nothing to do.")
#         return
    
#     while attempts:
#         with pyfgc.fgcs(converter) as fgc:
#             _ = fgc.set("REGFGC3.PROG.SLOT", slot)
#             _ = fgc.set("REGFGC3.PROG.DEBUG.ACTION", "SWITCH")

#             # Switching from production to download boots and viceversa may take ~10 seconds, according to Jose Luis
#             time.sleep(15)
#             _ = fgc.set("REGFGC3.SLOT_INFO", "")
#             if _is_board_in_download_boot(converter, slot):
#                 break

#             attempts -= 1
#             time.sleep(1)

#     else:
#         raise RuntimeError(f"Target: {board} in converter {converter}, could not switch back to download boot")
   
#     _module_logger.info(f"Target: board {board} in converter { converter} switched back to download boot")

def _is_board_in_requested_boot_mode(converter_data, boot_mode):
    global _module_logger
    converter, slot = converter_data

    slot_info = pyfgc.get(converter, "REGFGC3.SLOT_INFO").value
    slot_info_parsed = programmer.parse_slot_info(slot_info)
    
    if boot_mode.lower() == "downloadboot":
        return programmer.is_board_in_download_boot(slot_info_parsed[slot])

    else:
        return not programmer.is_board_in_download_boot(slot_info_parsed[slot])
    
def _switch_boards_boot(converter_data, boot_mode):
    MAX_ATTEMPTS_SWITCH = 3
    global _module_logger
    attempts_to_switch_boot_mode = MAX_ATTEMPTS_SWITCH
    converter, slot = converter_data

    if _is_board_in_requested_boot_mode(converter_data, boot_mode):
        _module_logger.info(f"Board in slot {slot} of converter {converter} already in boot mode {boot_mode}")
        return

    switch_success = False
    with pyfgc.fgcs(converter) as fgc:
        while attempts_to_switch_boot_mode:
            _ = fgc.set("REGFGC3.PROG.SLOT", slot)
            _ = fgc.set("REGFGC3.PROG.DEBUG.ACTION", "SWITCH")

            _module_logger.info(f"Waiting for board in slot {slot} to switch to {boot_mode}")
            time.sleep(10)

            _ = fgc.set("REGFGC3.SLOT_INFO", "")

            if _is_board_in_requested_boot_mode(converter_data, boot_mode):
                _module_logger.info(f"Board in slot {slot} of converter {converter} switched to {boot_mode}, attempt {MAX_ATTEMPTS_SWITCH - attempts_to_switch_boot_mode}")
                switch_success = True
                break

            attempts_to_switch_boot_mode -= 1
        
        else:
            _module_logger.info(f"Board in slot {slot} of converter {converter} DID NOT switch to {boot_mode} after three attempts")
            switch_success = False
    
    if not switch_success:
        raise pyfgc.PyFgcError

def _update_summary(summary_data):
    global prog_summary
    converter, board, device, attempts = summary_data
    
    if attempts == 3:
        prog_summary[converter][board][device].reprog_fail += 1

    elif attempts == 2:
        prog_summary[converter][board][device].reprog_3ed += 1

    elif attempts == 1:
        prog_summary[converter][board][device].reprog_2nd += 1

    elif attempts == 0:
        prog_summary[converter][board][device].reprog_1st += 1

def configure_logger(verbosity, log_file_name):
    default_severity = (verbosity == True) and logging.DEBUG or logging.INFO

    logger = logging.getLogger("pm_main")
    logger.setLevel(default_severity)

    LOG_FORMAT = "[%(asctime)s] [%(levelname)7s](%(module)11s): %(message)s"
    formatter = logging.Formatter(LOG_FORMAT)

    fh = handlers.RotatingFileHandler(log_file_name, maxBytes=1000000, backupCount=10)
    fh.setLevel(default_severity)
    fh.setFormatter(formatter)

    logger.addHandler(fh)

    logger.info("Loggers correctly configured")

    global _module_logger
    _module_logger = logger

def read_programming_data(data_file=PROGRAMMING_DATA_FILE):
    global tasks_per_converter_and_slot
    global prog_summary

    ProgDataRow = namedtuple(
        "ProgDataRow", "converter, slot, board, device, variant, var_rev, api_rev, bin_crc, fw_file_loc")

    with open(data_file, "r") as data_file:
        programming_data = [line.rstrip("\n").split(
            ",") for line in data_file if line[0] != "#"]

    for row in programming_data:
        pd_row = ProgDataRow(*row)
        tasks.append(pd_row)

        # Initialize tasks_per_converter_and_slot
        try:
            tasks_per_converter_and_slot[pd_row.converter]

        except KeyError:
            tasks_per_converter_and_slot[pd_row.converter] = dict()

        try:
            tasks_per_converter_and_slot[pd_row.converter][pd_row.slot] += 1

        except KeyError:
            tasks_per_converter_and_slot[pd_row.converter][pd_row.slot] = 1

        # Initialize prog_summary
        try:
            prog_summary[pd_row.converter]

        except KeyError:
            prog_summary[pd_row.converter] = dict()

        try:
            prog_summary[pd_row.converter][pd_row.board]

        except KeyError:
            prog_summary[pd_row.converter][pd_row.board] = dict()

        try:
            prog_summary[pd_row.converter][pd_row.board][pd_row.device]
            
        except KeyError:
            prog_summary[pd_row.converter][pd_row.board][pd_row.device] = ProgrammingSummary()

def program_loop():
    import random
    PROGRAMMING_REPETITIONS = 3
    global tasks
    global prog_summary
    global _module_logger

    total_iterations = 0

    for _ in range(PROGRAMMING_REPETITIONS):
        _module_logger.info(f"Programming loop iteration {_}")
        tasks_same_slot = dict()

        for task in tasks:
            _module_logger.info(f"Target: board {task.board}, device {task.device}, file {task.fw_file_loc}")
            
            try:
                _switch_boards_boot((task.converter, task.slot), "DownloadBoot")

            except pyfgc.PyFgcError as pe:
                _module_logger.error(pe)
                prog_summary[task.converter][task.board][task.device].to_db_fail += 1
                continue

            attempts = programmer.program(task.converter,
                                          task.slot,
                                          task.board,
                                          task.device,
                                          task.variant,
                                          task.var_rev,
                                          task.api_rev,
                                          task.bin_crc,
                                          os.path.join(os.path.expanduser(
                                              "~"), task.fw_file_loc),
                                          fgc_session=None)

            _update_summary((task.converter, task.board, task.device, attempts))

            try:
                tasks_same_slot[task.converter]

            except KeyError:
                tasks_same_slot[task.converter] = dict()

            try:
                tasks_same_slot[task.converter][task.slot] += 1

            except KeyError:
                tasks_same_slot[task.converter][task.slot] = 1

            if tasks_same_slot[task.converter][task.slot] == tasks_per_converter_and_slot[task.converter][task.slot]:
                _module_logger.info(f"All tasks done for slot {task.slot}, board {task.board}")

                try:
                    _switch_boards_boot((task.converter, task.slot), "ProductionBoot")

                except pyfgc.PyFgcError as pe:
                    _module_logger.error(pe)
                    prog_summary[task.converter][task.board][task.device].to_pb_fail += 1

        total_iterations += 1
    return total_iterations

def write_summary(total_iterations):
    global _module_logger
    global prog_summary

    _module_logger.info("SUMMARY")
    _module_logger.info(f"TOTAL iterations: {total_iterations}")

    for converter, c_dict in prog_summary.items():
        for board, b_dict in c_dict.items():
            for device, summary in b_dict.items():
                _module_logger.info(f"Converter: {converter}, board {board}, device {device}: {summary}")

if __name__ == "__main__":
    configure_logger(True, os.path.join(os.path.expanduser("~"), "pm_test", "program_manager.log"))
    read_programming_data()
    total_iterations = program_loop()
    write_summary(total_iterations)
