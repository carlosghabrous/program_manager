import pytest
from collections import namedtuple
# from unittest.mock import patch

import program_manager.regfgc3_programmer as programmer
from program_manager.regfgc3_programmer import parse_single_slot
from program_manager.regfgc3_programmer import parse_slot_info

SLOT_INFO_STRING = ("------------------------------,"
                    "SLOT       5,BOARD       VS_STATE_CTRL,STATE      DownloadBoot,"
                    "Device     DB,Variant    3,Var_Rev    208,API_Rev    200,,"
                    "Device     MF,Variant    0,Var_Rev    0,API_Rev    0,,"
                    "------------------------------,"
                    "SLOT       6,BOARD       VS_REG_DSP,STATE      DownloadBoot,"
                    "Device     DB,Variant    3,Var_Rev    205,API_Rev    200,,"
                    "Device     MF,Variant    0,Var_Rev    0,API_Rev    0,,"
                    "Device     DEVICE_2,Variant    0,Var_Rev    0,API_Rev    0,,"
                    "------------------------------,SLOT       9,BOARD       VS_ANA_INTK_2,STATE      ProductionBoot,"
                    "Device     MF,Variant    4,Var_Rev    21,API_Rev    1,,"
                    "------------------------------,SLOT       12,BOARD       VS_DIG_INTK,STATE      DownloadBoot,"
                    "Device     DB,Variant    3,Var_Rev    231,API_Rev    200,,"
                    "Device     MF,Variant    0,Var_Rev    0,API_Rev    0,,")

SINGLE_SLOT_INFO = ("SLOT       12, BOARD       VS_DIG_INTK, STATE      DownloadBoot,"
                    "Device     DB, Variant    3, Var_Rev    231, API_Rev    200, ,"
                    "Device     MF, Variant    0, Var_Rev    0, API_Rev    0, ,------------------------------")

PROG_DUMMY_DATA = ("RPAGM.866.21.ETH1", 4, "board", "device", "variant", 103, "my_file.bin")

def test_programmer_parse_single_slot_correctly():
    b = parse_single_slot(SINGLE_SLOT_INFO.split(","))
    assert b.SLOT == "12"
    assert b.BOARD == "VS_DIG_INTK"
    assert b.STATE == "DownloadBoot"
    assert b.devices[0].Device == "DB"
    assert b.devices[1].Device == "MF"
    assert b.devices[0].Variant == "3"
    assert b.devices[1].Variant == "0"
    assert b.devices[0].Var_Rev == "231"
    assert b.devices[1].Var_Rev == "0"
    assert b.devices[0].API_Rev == "200"
    assert b.devices[1].API_Rev == "0"

@pytest.mark.parametrize("slot, device, board, variant",
                    (("5", "DB", "VS_STATE_CTRL", "3"),
                    ("5", "MF", "VS_STATE_CTRL", "0"),
                     ("6", "DEVICE_2", "VS_REG_DSP", "0"),
                     ("9", "MF", "VS_ANA_INTK_2", "4"),
                     ("12", "DB", "VS_DIG_INTK", "3"),
                     ("12", "MF", "VS_DIG_INTK", "0")))
def test_programmer_slot_info_string_is_parsed_correctly(slot, device, board, variant):
    board, dev, var, *_ = parse_slot_info(slot, device, SLOT_INFO_STRING)
    assert board == board
    assert dev == device
    assert var == variant



