import pytest
from hypothesis import given
from hypothesis.strategies import integers, text, tuples

from program_manager.pm_fsm import PmState, PmStateWaiting, PmStateTransferred, PmStateProgrammed, PmStateSetProdBootPars, PmStateToProdBoot, PmStateCleanUp, PmStateError
from program_manager.pm_fsm import ProgramManagerFsm

ALLOWED_FSM_MODES = ["TRANSFERRED", "PROGRAMMED",
                     "SET_PROD_BOOT_PARS", "TO_PROD_BOOT", "CLEAN_UP", "WAITING"]
NOT_ALLOWED_FSM_MODES = [text() for _ in range(len(ALLOWED_FSM_MODES))]
PROG_DUMMY_DATA       = ("RPAGM.866.21.ETH1", 4, "card", "variant", 103, "my_file.bin")

# Helpers
def valid_modes_for_given_state(state):
    valid_modes_for_state = {
        PmStateWaiting: ("TRANSFERRED",),
        PmStateTransferred: ("PROGRAMMED",),
        PmStateProgrammed: ("SET_PROD_BOOT_PARS",),
        PmStateSetProdBootPars: ("TO_PROD_BOOT",),
        PmStateToProdBoot: ("CLEAN_UP",),
        PmStateCleanUp: ("WAITING",)}
    return valid_modes_for_state[state]

def invalid_modes_for_given_state(state):
    invalid_modes_for_state = {
        PmStateWaiting: (mode for mode in ALLOWED_FSM_MODES if mode != "TRANSFERRED"),
        PmStateTransferred: (mode for mode in ALLOWED_FSM_MODES if mode != "PROGRAMMED"),
        PmStateProgrammed: (mode for mode in ALLOWED_FSM_MODES if mode != "SET_PROD_BOOT_PARS"),
        PmStateSetProdBootPars: (mode for mode in ALLOWED_FSM_MODES if mode != "TO_PROD_BOOT"),
        PmStateToProdBoot: (mode for mode in ALLOWED_FSM_MODES if mode != "CLEAN_UP"),
        PmStateCleanUp: (mode for mode in ALLOWED_FSM_MODES if mode != "WAITING")}
    return invalid_modes_for_state[state]


# @given(tuples(text(), integers(), text(), text(), integers(), text()))
# def test_fsm_arguments_are_correctly_set(prog_data):
#     fsm = ProgramManagerFsm(prog_data)
#     assert fsm.converter  == prog_data[0]
#     assert fsm.slot       == prog_data[1]
#     assert fsm.card       == prog_data[2]
#     assert fsm.variant    == prog_data[3]
#     assert fsm.revision   == prog_data[4]
#     assert fsm.fw_file    == prog_data[5]

# @pytest.mark.parametrize("mode", [m for m in ALLOWED_FSM_MODES])
# def test_fsm_mode_is_settable_and_state_is_not(mode, state="state"):
#     fsm = ProgramManagerFsm(PROG_DUMMY_DATA)
#     fsm.mode = mode
#     assert fsm.mode == mode

#     with pytest.raises(AttributeError):
#         fsm.state = state

# @pytest.mark.parametrize("good_mode, bad_mode",
#     [(g, b) for g, b in zip(ALLOWED_FSM_MODES, NOT_ALLOWED_FSM_MODES)])
# def test_fsm_only_accepts_valid_modes(good_mode, bad_mode):
#     fsm = ProgramManagerFsm(PROG_DUMMY_DATA)
#     fsm.mode = good_mode
#     assert fsm.mode == good_mode

#     with pytest.raises(ValueError):
#         fsm.mode = bad_mode




@pytest.mark.parametrize("current_state, new_modes",
                         (
                             (PmStateWaiting, valid_modes_for_given_state(PmStateWaiting)),
                             (PmStateTransferred, valid_modes_for_given_state(PmStateTransferred)),
                             (PmStateProgrammed, valid_modes_for_given_state(PmStateProgrammed)),
                             (PmStateSetProdBootPars, valid_modes_for_given_state(PmStateSetProdBootPars)),
                             (PmStateToProdBoot, valid_modes_for_given_state(PmStateToProdBoot)),
                             (PmStateCleanUp, valid_modes_for_given_state(PmStateCleanUp)),
                            )
                        )
def test_fsm_accepts_only_valid_modes_for_a_given_state(current_state, new_modes):
    fsm = ProgramManagerFsm(PROG_DUMMY_DATA, init_state=current_state)
    for mode in new_modes:
        fsm.mode = mode
        assert fsm.mode == mode
    
@pytest.mark.parametrize("current_state, not_permitted_modes",
                         (
                            (PmStateWaiting, invalid_modes_for_given_state(PmStateWaiting)),
                            (PmStateTransferred, invalid_modes_for_given_state(PmStateTransferred)),
                            (PmStateProgrammed, invalid_modes_for_given_state(PmStateProgrammed)),
                            (PmStateSetProdBootPars, invalid_modes_for_given_state(PmStateSetProdBootPars)),
                            (PmStateToProdBoot, invalid_modes_for_given_state(PmStateToProdBoot)),
                            (PmStateCleanUp, invalid_modes_for_given_state(PmStateCleanUp)),
                            )
                         )
def test_fsm_raises_exception_if_mode_not_allowed_for_given_state(current_state, not_permitted_modes):
    fsm = ProgramManagerFsm(PROG_DUMMY_DATA, init_state=current_state)
    for mode in not_permitted_modes:
        with pytest.raises(ValueError):
            fsm.mode = mode

def test_fsm_moves_as_it_should():
    fsm = ProgramManagerFsm(PROG_DUMMY_DATA)
    modes = ALLOWED_FSM_MODES
    for mode in modes:
        fsm.mode = mode
        assert fsm.state == mode
    





