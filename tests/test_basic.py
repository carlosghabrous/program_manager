import pytest

# import program_manager


# class TestBasic(unittest.TestCase):

    # def test_start_stop(self):
    #     """Summary
    #     """
    #     import os
    #     import signal
    #     import subprocess
    #     import time

    #     with subprocess.Popen(["python", os.path.join(os.getcwd(), "program_manager", "pm_main.py")]) as proc:
    #         p_id = proc.pid
    #         time.sleep(2)
    #         os.kill(p_id, signal.SIGTERM)
            
    #     try:
    #         os.kill(p_id, 0)

    #     except OSError: 
    #         assert True

    #     else:
    #         assert False


    # def test_one_instance_only(self):
    #     """Summary
    #     """
    #     pass

# def test_start_stop_threads():
#     """Summary
#     """

#     scan = program_manager.scan.ScanThread(sleep_period_s=1)
#     prog = program_manager.codes_sync.CodesSyncThread(sleep_period_s=1)

#     scan.start()
#     prog.start()

#     assert scan.is_alive() == True
#     assert prog.is_alive() == True

#     import time
#     time.sleep(5)

#     scan.join()
#     prog.join()

#     assert scan.is_alive() == False
#     assert prog.is_alive() == False
