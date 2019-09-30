import logging
import queue
import threading
import time

import program_manager.adapters           as pm_adapters
import program_manager.regfgc3_programmer as programmer
import pyfgc


ITERATION_TIME_SEC = 5

import random


def get_expected_detected_differences(detected, expected):
    pass

def fgc_work(logger, job_name, adapter):
    logger.info(f"Getting expected data for {job_name}")

    # If not expected data, do not continue the work
    try:
        expected_data = adapter.get_expected(job_name)
        
    except FileNotFoundError:
        raise FileNotFoundError(f"expected data (file) not found for converter {job_name}")

    logger.info(f"{job_name} expected_data: {expected_data}")

    # Potential exceptions will be caught by the caller
    logger.info(f"Getting detected data for {job_name}")
    fgc = pyfgc.connect(job_name)
    try:
        #TODO: fix pyfgc and replace this line by fgc.get("REGFGC3.SLOT").value
        slot_info = fgc.get("REGFGC3.SLOT_INFO")[job_name].value
    
    except pyfgc.FgcResponseError:
        raise pyfgc.PyfgcError(f"did not get REGFGC3.SLOT_INFO from {job_name}")
    
    #TODO: try/except here not necessary once classes 62/63 have PM capabilities
    try:
        detected_data = programmer.parse_slot_info(slot_info)

    except TypeError:
        detected_data = None

    logger.info(f"{job_name} detected data: {detected_data}")

    # Compare and decide whether to program or not
    if expected_data == detected_data:
        logger.info(f"Nothing to do for {job_name}: expected data == detected data")
        return
        
    
    # detected_data = programmer.parse_slot_info(slot_info)
    # logger.info(f"{job_name} detected data: {detected_data}")
    # with pyfgc.fgcs(job_name) as fgc:
    #     # Get slot info
    #     slot_info = fgc.get("REGFGC3.SLOT_INFO")
    #     boards_info_fgc = programmer.parse_slot_info(slot_info)

    #     # Get expected from adapter
    #     logger.info(f"Get expected info from {job_name}")
    #     boards_info_adapter = 1
    
    #     # Decide whether to program or not
    #     if get_expected_detected_differences(boards_info_fgc, boards_info_adapter):
    #         logger.info(f"Expected != Detected for {job_name}. Let's program!")
    
    #         # Write what happened in log/DB
    #         logger.info(f"Writing in DB")
    #         time.sleep(random.randint(1, 5))

    #     logger.info(f"Job done. Reset flag")
    #     _ = fgc.set(job_name, "REGFGC3.PROG", "RESET")

    # logger.info(f"Applying faults policy...")

class FgcWorker(threading.Thread):
    def __init__(self, tasks, jobs, name="Anonymous"):
        super().__init__()
        self._tasks      = tasks
        self._jobs       = jobs
        self._lock       = threading.Lock()
        self.name        = name
        self._stop_event = threading.Event()
        self._logger     = logging.getLogger("pm_main." + __name__ + ".FgcWorker")

        self.start()

    def run(self):
        while not self._stop_event.is_set():
            try:
                func, job_name, adapter = self._tasks.get(timeout=2)

            except queue.Empty:
                self._logger.debug(f"FgcWorker({self.name}): queue empty, nothing to do")
                time.sleep(1)
                continue

            try:
                func(self._logger, job_name, adapter)

            #TODO: Program unsuccessful three times, converter in error if variants are different
            except FileNotFoundError as fe:
                self._logger.error(f"FgcWorker({self.name}): failed to reprogram {job_name}: {fe}")

            except pyfgc.PyFgcError as pe:
                self._logger.error(f"FgcWorker({self.name}): failed to reprogram {job_name}: {pe}")

            else:
                #TODO: we are here if expected and detected were retrieved successfully
                pass
                
            finally:
                self._tasks.task_done()
                with self._lock:
                    self._jobs.discard(job_name)
                
                self._logger.info(f"FgcWorker({self.name}): job {job_name} removed from tasks")

    def stop(self):
        self._stop_event.set()
    

class AreaProgramManager:
    MAX_NUM_TASKS   = 200
    MAX_NUM_WORKERS = 20

    def __init__(self, name, expected_data, adapter_data, num_workers=MAX_NUM_WORKERS):
        self.name          = name
        self._tasks        = queue.Queue(maxsize=AreaProgramManager.MAX_NUM_TASKS)
        self._workers      = list()
        self._jobs         = set()
        self._job_set_lock = threading.Lock()
        
        self._adapter = pm_adapters.get_adapter(expected_data, adapter_data)

        for i in range(num_workers):
            self._workers.append(FgcWorker(self._tasks, self._jobs, name=self.name+str(i)))
            
        self._logger = logging.getLogger("pm_main." + __name__)
        self._logger.info(f"AreaProgramManager({self.name}) created")

    def add_job(self, func, job_name):
        if not job_name in self._jobs:
            self._logger.debug(f"{job_name} not in TODO job list")

            with self._job_set_lock:
                self._jobs.add(job_name)

            self._tasks.put((func, job_name, self._adapter))
            self._logger.info(f"({self.name}) job {job_name} added to queue")

    def map(self, func, job_list):
        for job in job_list:
            self.add_job(func, job)

    def wait_completion(self):
        self._logger.info(f"({self.name}) waiting for pending tasks to be completed")
        self._tasks.join()
        self._logger.info(f"({self.name}) pending tasks are done")

        for worker in self._workers:
            worker.stop()
        
        self._logger.info(f"{self.name} workers stopped")
        
