"""Summary
"""

import logging
import threading
import time

import pyfgc
import pyfgc_name
import pyfgc_statussrv

from program_manager.area_worker import AreaProgramManager
from program_manager.area_worker import fgc_work


ITERATION_STATUS_SRV_SEC = 5
STATUS_SRV_REFRESH_SEC = 5

def _gen_fgc_jobs_for_groups_class(groups, class_id):
    pyfgc_name.read_name_file()
    pyfgc_name.read_group_file()

    for name, device in pyfgc_name.devices.items():
        if device["class_id"] != class_id:
            continue

        gr = pyfgc_name.gateways[device["gateway"]]["groups"][0]
        if gr not in groups:
            continue

        yield name, gr

def filter_jobs(status_rsp):
    for gw in status_rsp.keys():
        if status_rsp[gw]["recv_time_sec"] >= (time.time() - (STATUS_SRV_REFRESH_SEC * 2)):
            for dev in status_rsp[gw]["devices"].keys():
                try:
                    if "SYNC_REGFGC3" in status_rsp[gw]["devices"][dev]["ST_UNLATCHED"]:
                        device_obj = pyfgc_name.devices[dev]
                        yield dev, pyfgc_name.gateways[device_obj["gateway"]]["groups"][0]
                
                except KeyError:
                    pass

class ProgramManagerServer():
    def __init__(self, **kwargs):
        self.name_file     = kwargs["name_file"]
        self.fw_repo_loc   = kwargs["fw_repo_loc"]
        self.expected_data = kwargs["expected_data"]
        self.adapter_data  = kwargs["adapter_data"]
                
        self._run           = threading.Event()
        self._area_pms      = dict()
        
        self._status_srv_conn = None

        self._logger = logging.getLogger("pm_main." + __name__ + type(self).__name__)

    def start(self):
        self._logger.info("Starting Program Manager Server")
        pyfgc_name.read_name_file()
        pyfgc_name.read_group_file()

        for area in pyfgc_name.groups.keys():
            self._logger.info(f"Starting AreaProgramManager({area})")
            self._area_pms[area] = AreaProgramManager(area, self.expected_data, self.adapter_data)
                
        while not self._run.is_set():
            if not self._status_srv_conn:
                self._get_status_srv_connection()

            try:
                fgcds = pyfgc_statussrv.get_status_all(fgc_session=self._status_srv_conn)

            except pyfgc.PyFgcError as e:
                self._logger.warning(f"Error in ProgramManagerServer: {e}")
                self._clean_status_srv_connection()
                fgcds = dict()
            
            for device, area in filter_jobs(fgcds):
                self._area_pms[area].add_job(fgc_work, device)

            time.sleep(ITERATION_STATUS_SRV_SEC)

            
    def _get_status_srv_connection(self):
        try:
            #TODO: delay throwing exceptions in pyfgc, but throw them
            self._status_srv_conn = pyfgc.connect("FGC_STATUS")
            
        except pyfgc.PyFgcError as pe:
            self._logger.warning(f"Could not establish connection with status server {pe}")
            self._clean_status_srv_connection()
            
    def _clean_status_srv_connection(self):
        if self._status_srv_conn:
            self._status_srv_conn.disconnect()
            self._status_srv_conn = None

    def stop(self):
        self._logger.info("Stopping Program Manager Server")
        self._run.set()
        for area in self._area_pms.keys():
            self._area_pms[area].wait_completion()
        
        if self._status_srv_conn:
            self._status_srv_conn.disconnect()
            self._status_srv_conn = None
        
        self._logger.info("Program Manager Server stopped")
