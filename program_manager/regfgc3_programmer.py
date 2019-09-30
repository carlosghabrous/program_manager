"""regfgc3_programmer

Usage:
    regfgc3_programmer.py -h | --help
    regfgc3_programmer.py [-v | --verbosity] [-l | --loose] <converter> <slot> <board> <device> <variant> <var_revision> <api_revision> <fw_file_loc>

Options:
    -h --help       Show this help. 
    -v --verbosity  Increase output verbosity [default: INFO].
    -l --loose      Upgrade FW even if variant in board differs from input argument.     
"""

import logging
import os
import re
import sys
from collections import namedtuple
from logging import handlers

import docopt
import termcolor

import program_manager.pm_fsm as fsm
import pyfgc

DEVICES_LIST  = ["DB", "MF"] + ["DEVICE_" + str(i) for i in range(2, 6)]
FW_FILE_REGEX = re.compile(r"EDA_\d{1,5}-([A-Z]{2,6}_*\d*)-([A-Z]+_\d+)-(\d*)-(\d*)-([0-9A-Z]{4}).bin")
LOG_FILE_NAME = "program_manager.log"

_module_logger = logging.getLogger("pm_main." + __name__)

def _configure_logger(verbosity):
    default_severity = verbosity and logging.DEBUG or logging.INFO
    logger = logging.getLogger(__name__)
    logger.setLevel(default_severity)

    LOG_FORMAT = "[%(asctime)s] - [%(levelname)8s](%(module)10s): %(message)s"
    formatter = logging.Formatter(LOG_FORMAT)
    fh = handlers.RotatingFileHandler(LOG_FILE_NAME, maxBytes=1000000, backupCount=10)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(default_severity)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)
    global _module_logger
    _module_logger = logger
    
def _args_dict_to_tuple(args, bin_crc):
    return (args["<converter>"],
            args["<slot>"],
            args["<board>"],
            args["<device>"],
            args["<variant>"],
            args["<var_revision>"],
            args["<api_revision>"],
            bin_crc,
            args["<fw_file_loc>"])

def _get_crc_from_name(fw_file_loc):
    base, filename = os.path.split(fw_file_loc)
    filename = filename or os.path.basename(base)

    bin_crc = FW_FILE_REGEX.search(filename).group(5)
    return bin_crc

def _run_security_checks(cmd_info, fgc_info, fw_file_loc, loose_option):
    # Device in possible values
    global _module_logger
    try:
        assert cmd_info.device in DEVICES_LIST

    except AssertionError:
        _module_logger.critical(f"Command line device {cmd_info.device} is not a valid device. Possible values are {','.join(DEVICES_LIST)}. Exiting...")
        sys.exit(2)

    # board
    try:
        assert cmd_info.board == fgc_info.board

    except AssertionError:
        _module_logger.critical(f"Command line board {cmd_info.board} is different than fgc board {fgc_info.board}. Board programming NOT ALLOWED! Exiting...")
        sys.exit(2)

    try:
        assert fgc_info.device == cmd_info.device

    except AssertionError:
        _module_logger.critical(f"Command line device {cmd_info.device} is different than fgc device {fgc_info.device}. Board programming NOT ALLOWED! Exiting...")
        sys.exit(2)

    # Variant
    try:
        assert fgc_info.variant == cmd_info.variant

    except AssertionError:
        variant_msg = f"Command line variant {cmd_info.variant} is different than fgc variant {fgc_info.variant}."
        if loose_option:
            _module_logger.warning(variant_msg)
        
        else:
            _module_logger.critical(variant_msg + "board programming NOT ALLOWED!. Exiting...")
            sys.exit(2)

    _module_logger.info("Input argumets successfully validated!")

    # File
    try:
        _check_file_consistency(cmd_info.variant, cmd_info.device, cmd_info.var_rev, fw_file_loc)

    except (AssertionError, AttributeError, FileNotFoundError) as ae:
        _module_logger.critical(f"{ae}. Exiting...")
        sys.exit(2)
    
    else:
        _module_logger.info("File naming consistency successfully validated!")

    # All OK
    if not loose_option:
        if cmd_info.var_rev == fgc_info.var_rev:
            nothing_todo_msg = "Nothing to do: cmd line variant {cmd_info.variant} = fgc variant {fgc_info.variant};"
            nothing_todo_msg += "cmd line var_revision {cmd_info.var_rev} = fgc var_revision {fgc_info.var_rev}. Exiting..."
            _module_logger.info(nothing_todo_msg)
            sys.exit(0)

def _get_fgc_detected(converter, slot, device):
    slot_info = ""
    try:
        r = pyfgc.get(converter, "REGFGC3.SLOT_INFO")
        slot_info = r.value

    except pyfgc.FgcResponseError:
        _module_logger.error(f"{r.err_code}: {r.err_msg}")
        sys.exit(2)

    except RuntimeError as re:
        _module_logger.error(re)
        sys.exit(2)

    boards = parse_slot_info(slot_info)
    board, dev, variant, var_rev, api_rev = [""] * 5

    try:
        b = boards[slot]
    
    except KeyError:
        _module_logger.error(f"Board not found in slot {slot}!")
        sys.exit(1)

    if not is_board_in_download_boot(b):
        _module_logger.error(f"Board {b['board']} is not running in DownloadBoot!")
        sys.exit(1)

    try:
        device = b["devices"][device]

    except KeyError:
        _module_logger.error(f"Device {device} not found in slot {slot}, board {b['board']}!")
        sys.exit(1)

    board, dev, variant, var_rev, api_rev = b["board"], device.Device, device.Variant, device.Var_Rev, device.API_Rev

    return board, dev, variant, var_rev, api_rev

def _parse_single_slot(single_slot):
    Board   = namedtuple("Board", "SLOT, BOARD, STATE, devices")
    Device  = namedtuple("Device", "Device, Variant, Var_Rev, API_Rev")

    single_slot.pop()
    devices          = dict()
    board_info_dict  = dict()

    dev_pos = [i for i, element in enumerate(single_slot) if element.startswith("Device")]
    for i in range(len(dev_pos)):
        idx_tuple = dev_pos[i:i+2]
        if len(idx_tuple) == 1:
            single_device_info = single_slot[idx_tuple[0]:]
        else:
            single_device_info = single_slot[idx_tuple[0]:idx_tuple[1]]

        device_dict = dict([el.split() for el in single_device_info if el.strip()])
        dev = Device(**device_dict)
        devices.update({dev.Device: dev})

    board_info_dict = dict([el.split() for el in single_slot[0:3]])
    board_info_dict["devices"] = devices
    return Board(**board_info_dict)

def _check_file_consistency(cmd_variant, cmd_device, cmd_var_revision, fw_file_loc):
    """Checks file's name against naming convention.

    Checks file's name follows naming convention, and also that its different 
    name's parts are consistent with the user's input. 
    Raises an AttributeError if the file did not match the regex.
    Raises an AssertionError if file differs from user's input.

    Arguments:
        cmd_variant {[type]}        -- User's input variant
        cmd_device {[type]}         -- User's input device
        cmd_var_revision {[type]}   -- User's input revision
        fw_file_loc {[type]}        -- User's input binary file
    """
    global _module_logger

    _module_logger.info("Checking if fw file exists...")
    base_dir, fw_file = os.path.split(fw_file_loc)
    fw_file = fw_file or os.path.basename(base_dir)

    fw_fileh = None
    try:
        fw_fileh = open(fw_file_loc, "r+b")

    except FileNotFoundError:
        raise FileNotFoundError(f"Could not open firmware file {fw_file_loc}!")
    
    finally:
        if fw_fileh is not None:
            fw_fileh.close()
    
    _module_logger.info(f"File {fw_file} in directory {base_dir} found!")

    _module_logger.info("Checking fw file naming consistency...")
    m = FW_FILE_REGEX.search(fw_file)
    try:
        dev, var, rev = m.group(1), m.group(2), m.group(3)

    except AttributeError:
        raise AttributeError(f"Firmware file '{fw_file}' does not conform to naming standards")

    if var != cmd_variant:
        raise AssertionError(f"File variant {var} is different than cmd input variant {cmd_variant}")

    if dev != cmd_device:
        raise AssertionError(f"File device {dev} is different than cmd input device {cmd_device}")

    if rev != cmd_var_revision:
        raise AssertionError(f"File revision {rev} is different than cmd input revision {cmd_var_revision}")

def is_board_in_download_boot(board):
    if board["state"] != "DownloadBoot":
        return False

    try:
        db_device = board["devices"]["DB"]

    except KeyError:
        return False

    if db_device.Variant != "DOWNLDBOOT_3":
        return False

    return True 

def parse_slot_info(slot_info_reply):
    si_list        = slot_info_reply.split(",")
    slot_start_pos = [idx for idx, element in enumerate(si_list) if element.startswith("SLOT")]
    boards         = dict()
    
    for i in range(len(slot_start_pos)):
        idx_tuple = slot_start_pos[i : i+2]
        if len(idx_tuple) == 1:
            single_slot_info = si_list[idx_tuple[0]:]
        else:
            single_slot_info = si_list[idx_tuple[0]:idx_tuple[1]]

        slot_dict = _parse_single_slot(single_slot_info)
        boards.update({slot_dict.SLOT:{"board":slot_dict.BOARD, "state":slot_dict.STATE, "devices":slot_dict.devices}})
    
    return boards

def program(converter, slot, board, device, variant, var_revision, api_revision, bin_crc, fw_file_loc, fgc_session=None):
    global _module_logger
    max_attempts = 3
    #TODO: temporary for programming in loop
    attempts = 0

    for n in range(max_attempts):
        pm_fsm = fsm.ProgramManagerFsm((converter, slot, board, device, variant, var_revision, api_revision, bin_crc, fw_file_loc),
                                        fgc_session,
                                        logger=_module_logger)
        try:
            pm_fsm.process()

        except RuntimeError:
            _module_logger.error(f"Error in {converter} while reprogramming {device} in board {board} (attempt {n+1})")
            pm_fsm.reset()
            del pm_fsm
        
        else:
            _module_logger.info(f"{converter}: device {device} on board {board} successfully reprogrammed")
            attempts = n
            break
    
    else:
        _module_logger.critical(f"{converter}: reached maximum programming attempts. Device {device} on {board} was NOT successfully reprogrammed")
        attempts = 3
        # if __name__ != "__main__":
        #     #TODO: what kind of exception?
        #     raise Exception

    return attempts

def main():
    args = docopt.docopt(__doc__)
    _configure_logger(args["--verbosity"])
    _module_logger.debug(f"Cmd line arguments: {args}")
    ProgramInfo = namedtuple("ProgramInfo", "converter, board, device, variant, var_rev, api_rev")

    fgc_info = ProgramInfo(args["<converter>"], *_get_fgc_detected(args["<converter>"], args["<slot>"], args["<device>"]))
    cmd_info = ProgramInfo(args["<converter>"], args["<board>"], args["<device>"], args["<variant>"], args["<var_revision>"], args["<api_revision>"])

    # Run security checks
    _module_logger.info("Running security checks...")
    _run_security_checks(cmd_info, fgc_info, args["<fw_file_loc>"], args["--loose"])
    bin_crc = _get_crc_from_name(args["<fw_file_loc>"])

    msg_reprog_basic_info = termcolor.colored(
        f"DEVICE: {fgc_info.device} from BOARD: {fgc_info.board} (slot{args['<slot>']}) in CONVERTER {cmd_info.converter} will be programmed.",
        "yellow",
        attrs=["bold"])

    msg_reprog_variants = termcolor.colored(
        f"{'VARIANT(old)':<13}: {fgc_info.variant:<13} ---> {'VARIANT(new)':<13}: {cmd_info.variant}",
        "red",
        attrs=["bold"])

    msg_reprog_revisions = termcolor.colored(
        f"{'REVISION(old)':<13}: {fgc_info.var_rev:<13} ---> {'REVISION(new)':<13}: {cmd_info.var_rev}",
        "red",
        attrs=["bold"])

    msg_confirmation = termcolor.colored("PROCEED? [Y/n]", "green", attrs=["bold"])

    _module_logger.warning(msg_reprog_basic_info)
    _module_logger.warning(msg_reprog_variants)
    _module_logger.warning(msg_reprog_revisions)
    _module_logger.warning(termcolor.colored(f"{'Binary file':<13}: {args['<fw_file_loc>']}", "red", attrs=["bold"]))
    _module_logger.warning(msg_confirmation)
    
    try:
        confirmation = str(input())

    except KeyboardInterrupt:
        _module_logger.info("Action cancelled by user. Exiting...")
        sys.exit(0)
    
    else:
        if confirmation != "Y" and confirmation.lower() != "n":
            _module_logger.warning("Unknown option. Exiting...")
            sys.exit(2)

        if confirmation.lower() == "n":
            _module_logger.info("Action cancelled by user. Exiting...")
            sys.exit(0)
    
    try:
        program(*_args_dict_to_tuple(args, bin_crc))

    except RuntimeError:  
        _module_logger.error(f"Maximum attempts to reprogram {cmd_info.converter} reached: board {cmd_info.board}, device {cmd_info.device}")
        sys.exit(2)

if __name__ == "__main__":
    main()
