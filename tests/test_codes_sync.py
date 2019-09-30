from unittest import mock

import pytest

from program_manager import codes_sync

def test_mock_object():

    my_mock = mock.Mock()
    my_mock.get_that_thing()

    my_mock.get_that_thing.assert_called_once()

def test_edms_released():
    pass

def test_nfs_released():
    pass

def test_sync_released():
    pass

