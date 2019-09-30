import logging
import os
from collections import namedtuple

def get_adapter(adapter, adapter_data):
    if adapter == "db":
        return DbAdapter(*adapter_data)

    if adapter == "fs":
        return FileSystemAdapter(*adapter_data)

    if adapter == "ls":
        return LocalFileSystemAdapter()


class Adapter:
    Device = namedtuple("Device", "Device, Variant, Var_Rev, API_Rev")

    def __init__(self, **kwargs):
        pass

    def get_expected(self, fgc_name):
        pass

    def get_detected(self):
        pass

    def record_detected(self):
        pass


class DbAdapter(Adapter):
    #TODO: use Borg idiom to share state?
    RELEASE_INFO_TABLE    = ""
    RECORD_DETECTED_TABLE = ""
    
    def __init__(self, connection_string, username, password, fw_file_loc):
        self._logger = logging.getLogger("pm_main." + __name__)
        self._logger.info(f"Adapter {type(self).__name__} created")

    def get_detected(self):
        raise NotImplementedError

    def get_expected(self):
        raise NotImplementedError

    def record_detected(self):
        raise NotImplementedError

class FileSystemAdapter(Adapter):
    def __init__(self, fw_subfolder, db_subfolder, fw_file_loc):
        self._db_files = os.path.join(fw_file_loc, db_subfolder)
        self._fw_files = os.path.join(fw_file_loc, fw_subfolder)
        
        self._converter_last_time_updated = dict()

        self._logger = logging.getLogger("pm_main." + __name__)
        self._logger.info(f"Adapter {type(self).__name__} created")

    def get_detected(self):
        raise NotImplementedError

    def get_expected(self, fgc_name):
        expected_data = None
        expected_converters = os.listdir(self._db_files)

        if fgc_name not in expected_converters:
            raise FileNotFoundError
                
        expected_converter_file = os.path.join(self._db_files, fgc_name)
        last_time_updated       = int(os.path.getmtime(expected_converter_file))
        
        try:
            last_time = self._converter_last_time_updated[fgc_name]
        
        except KeyError:
            self._converter_last_time_updated[fgc_name] = last_time_updated
            expected_data = self._parse_expected_file(expected_converter_file)
        
        else:
            if last_time_updated > last_time:
                expected_data = self._parse_expected_file(expected_converter_file)
        
        return expected_data


    def record_detected(self):
        raise NotImplementedError

    def _parse_expected_file(self, file_name):
        #TODO: protect access to file? One thread should only access one file, so might not be needed
        lines         = list()
        expected_data = dict()

        with open(file_name, "r") as f:
            lines = f.readlines()
        
        for l in lines:
            if l.startswith("#"):
                continue

            l = l.strip()
            slot, board, *dev_info = l.split(",")
            dev = Adapter.Device(*dev_info)

            try:
                expected_data[slot]

            except KeyError:
                expected_data[slot] = dict()
                expected_data[slot] = {"board": board, "devices": dict()}

            expected_data[slot]["devices"].update({dev.Device: dev})

        return expected_data

class LocalFileSystemAdapter(Adapter):
    DETECTED_DATA = ""
    EXPECTED_DATA = ""
    INSERTED_DATA = ""

    def __init__(self, detected_data=DETECTED_DATA,
                        expected_data=EXPECTED_DATA,
                        inserted_data=INSERTED_DATA):
        self.detected = detected_data
        self.expected = expected_data
        self.inserted = inserted_data
    
    def get_expected(self, fgc_name):
        with open(self.expected, "r") as efh:
            pass

    def get_detected(self):
        with open(self.detected, "r") as dfh:
            pass

    def record_detected(self):
        with open(self.inserted, "w") as ifh:
            pass
