"""program_manager

Usage:
    program_manager [-v] [-c --config-file=<C>]
    program_manager -h | --help

Options:
    -h --help           Show this help.
    -v --verbosity      Increase output verbosity [default: INFO].
    -c --config-file C  Program Manager configuration file location [default: ../data/pm_config.cfg].
"""

# Imports 
import docopt
import logging
import os
import signal
import sys

from configparser import SafeConfigParser
from logging import handlers

from pm_server import ProgramManagerServer

class ProgramManagerTermError(Exception):
    def __init__(self, signum, frame):
        self.logger = logging.getLogger("pm_main")
        self.logger.error(f"Signal {signum} received")


def shutdown_pm(signum, frame):
    raise ProgramManagerTermError(signum, frame)

def start_pm(log, config_info):
    signal.signal(signal.SIGTERM, shutdown_pm)
    signal.signal(signal.SIGINT, shutdown_pm)
    
    log.info("Signal handlers configured")

    pms = None
    try:
        pms = ProgramManagerServer(name_file     = config_info["name_file"],
                                   fw_repo_loc   = config_info["fw_repo_loc"],
                                   expected_data = config_info["expected_data"],
                                   adapter_data  = config_info["adapter_data"])
        pms.start()
    
    except ProgramManagerTermError:
        if pms:
            pms.stop()
        log.info("ProgramManagerServer terminated. Exiting...")
        sys.exit(0)

    except Exception as e:
        if pms:
            pms.stop()
        log.exception(e)
        sys.exit(2)


def configure_logger(verbosity, log_file_name):
    default_severity = (verbosity == True) and logging.DEBUG or logging.INFO

    logger = logging.getLogger("pm_main")
    logger.setLevel(default_severity)

    LOG_FORMAT = "[%(asctime)s] [%(levelname)7s](%(module)11s): %(message)s"
    formatter = logging.Formatter(LOG_FORMAT)
    
    full_path_to_log_file = os.path.expanduser(os.path.join("~", log_file_name))
    fh = handlers.RotatingFileHandler(full_path_to_log_file, maxBytes=1000000, backupCount=10)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(default_severity)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    logger.info("Loggers correctly configured")
    return logger

def read_config_file(config_file_name:str) -> None:
    config = SafeConfigParser()
    config.read(args["--config-file"])

    name_file     = config.get("BASIC", "name_file_location")
    fw_repo_loc   = config.get("BASIC", "fs_fw_repo_location")
    expected_data = config.get("BASIC", "expected_data_location")
    log_file_name = config.get("BASIC", "pm_log_file_name")

    conn_string, username, password = [""] * 3
    fw_subfolder, db_subfolder      = [""] * 2

    if expected_data == "db":
        conn_string  = config.get("db", "connection_string")
        username     = config.get("db", "username")
        password     = config.get("db", "password")
        adapter_data = [conn_string, username, password]

    if expected_data == "fs":
        fw_subfolder = config.get("fs", "fw_subfolder")
        db_subfolder = config.get("fs", "db_subfolder")
        adapter_data = [fw_subfolder, db_subfolder]

    adapter_data.append(fw_repo_loc)
    config_file_dict = dict(zip(
                                ("name_file", "fw_repo_loc", "log_file_name", "expected_data", "adapter_data"),
                                (name_file,    fw_repo_loc,   log_file_name,   expected_data,  tuple(adapter_data))
                                )
                            )
    
    return config_file_dict
    

# Program Manager entry point
if __name__ == "__main__":
    args        = docopt.docopt(__doc__)
    config_info = read_config_file(args["--config-file"])
    log         = configure_logger(args["--verbosity"], config_info["log_file_name"])
    start_pm(log, config_info)
