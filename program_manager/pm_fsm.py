import logging
import os
import time

from binascii     import hexlify
from collections  import namedtuple
from functools    import partial

import pyfgc

CHARS_PER_WORD       = 8
FW_FILE_LIMIT_BYTES  = 4194304
LIMIT_GW_CMD_WORDS   = 66100

class PmState:
    def __init__(self, logger, name="", timeout=30):
        self.name = name
        self.timeout = timeout
        self._logger = logger

    def run(self, fgc_session, **kwargs):
        while self.timeout:
            fgc_state = fgc_session.get("REGFGC3.PROG.FSM.STATE")
            self._logger.debug(f"FGC PM FSM state after polling: {fgc_state.value}")

            if fgc_state.value == self.name:
                break

            time.sleep(3)
            self.timeout -= 3
        
        else:
            board_error = fgc_session.get("REGFGC3.PROG.DEBUG.BOARD_ERROR")
            last_state  = fgc_session.get("REGFGC3.PROG.FSM.LAST_STATE")
            raise RuntimeError(f"Timeout: FGC did not reach state {self.name} (last state: {last_state.value}, board error: {board_error.value})")
            
        self._logger.info(f"FGC PM FSM state {self.name} processed successfully")

    def __repr__(self):
        return f"PmState('{self.name}')"

class PmStateUninitialized(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="UNINITIALIZED")

class PmStateWaiting(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="WAITING")
    
    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateTransferring(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="TRANSFERRING")
    
    def run(self, fgc_session, **kwargs):
        slot, device, variant, var_revision, api_revision, bin_crc, fw_file_loc = (
            kwargs["slot"],
            kwargs["device"],
            kwargs["variant"],
            kwargs["var_revision"],
            kwargs["api_revision"],
            kwargs["bin_crc"],
            kwargs["fw_file_loc"])

        try:
            fw_file_info = os.stat(fw_file_loc)

        except FileNotFoundError as fnfe:
            raise RuntimeError(f"{fnfe}")

        if not fw_file_info.st_size:
            raise RuntimeError(f"File's {fw_file_loc} is empty. Nothing to do...")

        if fw_file_info.st_size > FW_FILE_LIMIT_BYTES:
            raise RuntimeError(f"File's {fw_file_loc} size {fw_file_info.st_size} over limit {FW_FILE_LIMIT_BYTES}")

        packet = list()
        with open(fw_file_loc, "r+b") as fwh:
            for word in iter(partial(fwh.read, 4), b""):
                # Bin into hex and decode
                ascii_word = hexlify(word).decode()
                # Add padding
                ascii_word += "".join(["0"] * (CHARS_PER_WORD - len(ascii_word)))
                packet.append(hex(int(ascii_word, 16)))
                
        _ = fgc_session.set("REGFGC3.PROG.SLOT"             ,slot)
        _ = fgc_session.set("REGFGC3.PROG.DEVICE"           ,device)
        _ = fgc_session.set("REGFGC3.PROG.VARIANT"          ,variant)
        _ = fgc_session.set("REGFGC3.PROG.VARIANT_REVISION" ,var_revision)
        _ = fgc_session.set("REGFGC3.PROG.API_REVISION"     ,api_revision)
        _ = fgc_session.set("REGFGC3.PROG.BIN_SIZE_BYTES"   ,fw_file_info.st_size)
        _ = fgc_session.set("REGFGC3.PROG.BIN_CRC"          ,int(bin_crc, 16))
        for i in range(0, len(packet), LIMIT_GW_CMD_WORDS):
            fgc_session.set(f"REGFGC3.PROG.BIN[{i},]", ",".join(packet[i:i + LIMIT_GW_CMD_WORDS]))

        # Leave FGC time to digest
        time.sleep(5)
        super().run(fgc_session, **kwargs)

class PmStateTransferred(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="TRANSFERRED")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateGetProgInfo(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="GET_PROG_INFO")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateProgramming(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="PROGRAMMING")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateProgramCheck(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="PROG_CHK")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateProgrammed(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="PROGRAMMED")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateSetProdBootPars(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="SET_PB_PARS")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateToProdBoot(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="TO_PROD_BOOT")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateCleanUp(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="CLEAN_UP")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class PmStateError(PmState):
    def __init__(self, logger):
        super().__init__(logger, name="ERROR")

    def run(self, fgc_session, **kwargs):
        super().run(fgc_session, **kwargs)

class ProgramManagerFsm:
    STATE_TO_MODE_TO_INTERIM_STATES = {
        "UNINITIALIZED"       : {"WAITING"             : [PmStateWaiting]},
        "WAITING"             : {"TRANSFERRED"         : [PmStateTransferring, PmStateTransferred]},
        "TRANSFERRED"         : {"PROGRAMMED"          : [PmStateGetProgInfo, PmStateProgramming, PmStateProgramCheck, PmStateProgrammed]},
        "PROGRAMMED"          : {"SET_PB_PARS"         : [PmStateSetProdBootPars]},
        "SET_PB_PARS"         : {"TO_PROD_BOOT"        : [PmStateToProdBoot]},
        "TO_PROD_BOOT"        : {"CLEAN_UP"            : [PmStateCleanUp]},
        "CLEAN_UP"            : {"WAITING"             : [PmStateWaiting]},
        "ERROR"               : {"CLEAN_UP"            : [PmStateCleanUp]}
    }

    VALID_MODES = set()
    for _, mode_to_inter_states_dict in STATE_TO_MODE_TO_INTERIM_STATES.items():
        VALID_MODES.add(list(mode_to_inter_states_dict.keys())[0])

    def __init__(self, prog_data, fgc_session, init_state=PmStateUninitialized, logger=None):
        self.prog_data_dict = dict(zip(("converter",
                                "slot",
                                "board",
                                "device",
                                "variant",
                                "var_revision",
                                "api_revision",
                                "bin_crc",
                                "fw_file_loc"), prog_data))

        self._fgc_session         = fgc_session
        self._fgc_session_created = False
        self._mode                = "UNINITIALIZED"
        self._logger              = logger or logging.getLogger("pm_main." + __name__)
        self._current_state       = init_state(self._logger)
        
        self._set_valid_fgc_connection()

    def process(self):
        try:
            assert isinstance(self._current_state, PmStateUninitialized)
        
        except AssertionError:
            self._logger.exception(f"Initial FSM state '{self.state}' should be 'UNINITIALIZED'")
            return
        
        mode_sequence          = list(ProgramManagerFsm.VALID_MODES)
        error_during_reprogram = False
        
        while mode_sequence:
            mode = list(ProgramManagerFsm.STATE_TO_MODE_TO_INTERIM_STATES[self.state].keys())[0]
            self._logger.info(f"processing mode {mode} in state {self.state}")

            try:
                self._process_mode(mode, self._fgc_session)

            except (RuntimeError, KeyError) as e:
                self._logger.error(f"{e}")
                # Exit if an error was already registered
                if error_during_reprogram:
                    mode_sequence = []
                
                # Try to recover if first time error happens
                else:
                    error_during_reprogram = True
                    self._current_state = PmStateError(self._logger)
                    mode_sequence = ["CLEAN_UP"]

            else:
                _ = mode_sequence.pop(0)

        # Try to leave the FGC FSM in its initial state
        try:
            self._process_mode("WAITING", self._fgc_session)

        except KeyError as e:
            raise RuntimeError(e)
        
        if error_during_reprogram:
            raise RuntimeError("Error during reprogramming after recovery attempt")

    def _set_valid_fgc_connection(self):
        # Create connection if the client did not do it
        if self._fgc_session:
            return

        try:
            self._fgc_session = pyfgc.connect(self.prog_data_dict["converter"])

        except pyfgc.PyFgcError as pe:
            raise RuntimeError(pe)
        
        else:
            self._fgc_session_created = True

    #TODO: call reset internally? See uses cases. 
    def reset(self):
        self._mode          = "UNINITIALIZED"
        self._current_state = PmStateUninitialized(self._logger)

        # Only close the connection if it was created here (otherwise it is the client's connection)
        if self._fgc_session_created:
            try:
                self._fgc_session.disconnect()

            except pyfgc.PyFgcError as pe:
                self._logger.exception(f"Could not close connection to the FGC: {pe}")

    def _process_mode(self, target_mode, fgc_session):
        self._mode = target_mode
        interim_states = ProgramManagerFsm.STATE_TO_MODE_TO_INTERIM_STATES[self.state][target_mode]

        for interim_state in interim_states:
            _ = fgc_session.set("REGFGC3.PROG.FSM.MODE", target_mode)
            next_state = interim_state(self._logger)
            if self._current_state.name == next_state.name:
                pass

            else:
                next_state.run(fgc_session, **self.prog_data_dict)
                self._current_state = next_state

    @property
    def state(self):
        return self._current_state.name

    @property
    def mode(self):
        return self._mode

    #TODO: the setter is only valid for commissioning/testing.
    @mode.setter
    def mode(self, new_mode):
        mode_for_current_state = list(ProgramManagerFsm.STATE_TO_MODE_TO_INTERIM_STATES[self.state].keys())[0]
        try:
            assert new_mode == mode_for_current_state
        
        except AssertionError:
            raise AssertionError(f"Mode {new_mode} not allowed for current state {self.state}")

        else:
            self._process_mode(new_mode, self._fgc_session)
    
    def __str__(self):
        return f"<ProgramManagerFsm: {self.mode}, {self.state}>"
