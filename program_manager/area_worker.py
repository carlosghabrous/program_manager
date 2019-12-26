import logging
import queue
import threading
import time


ITERATION_TIME_SEC = 5

import random

def fgc_work(logger, job_name):
    # Get slot info
    logger.info(f"Get SLOT_INFO from {job_name}")
    time.sleep(random.randint(1, 5))
    
    # Get expected
    logger.info(f"Get expected info from {job_name}")
    time.sleep(random.randint(1, 5))
    
    # Decide whether to program or not
    logger.info(f"Expected != Detected for {job_name}. Let's program!")
    time.sleep(random.randint(1, 20))
    
    # Write what happened in log/DB
    logger.info(f"Writing in DB")
    time.sleep(random.randint(1, 5))

class FgcWorker(threading.Thread):
    def __init__(self, tasks, jobs, lock, name="Anonymous"):
        super().__init__()
        self._tasks      = tasks
        self._jobs       = jobs
        self._lock       = lock
        self.name        = name
        self._stop_event = threading.Event()
        self._logger     = logging.getLogger("pm_main." + __name__ + ".FgcWorker")

        self.start()

    def run(self):
        while not self._stop_event.is_set():
            try:
                func, job_name = self._tasks.get(timeout=2)

            except queue.Empty:
                self._logger.debug(f"FgcWorker({self.name}): queue empty, nothing to do")
                time.sleep(1)
                continue

            try:
                func(self._logger, job_name)

            except Exception:
                #TODO: Program unsuccessful three times, converter in error if variants are different
                self._logger.error(f"FgcWorker({self.name}): failed to reprogam {job_name}, setting the converter in error")
                
            finally:
                self._tasks.task_done()
                with self._lock:
                    self._jobs.discard(job_name)
                
                self._logger.info(f"FgcWorker({self.name}): job {job_name} removed from tasks")

    def stop(self):
        self._stop_event.set()
    

class AreaProgramManager:
    MAX_NUM_TASKS = 200
    MAX_NUM_WORKERS = 20

    def __init__(self, name="", num_workers=MAX_NUM_WORKERS):
        self.name          = name
        self._tasks        = queue.Queue(maxsize=AreaProgramManager.MAX_NUM_TASKS)
        self._workers      = list()
        self._jobs         = set()
        self._job_set_lock = threading.Lock()
        
        for i in range(num_workers):
            self._workers.append(FgcWorker(self._tasks, self._jobs, self._job_set_lock, name=self.name+str(i)))
            
        self._logger = logging.getLogger("pm_main." + __name__)
        self._logger.info(f"AreaProgramManager({self.name}) created")

    def add_job(self, func, job_name):
        if not job_name in self._jobs:
            self._logger.debug(f"{job_name} not in jobs")

            with self._job_set_lock:
                self._jobs.add(job_name)

            self._tasks.put((func, job_name))
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
        