"""Reads the binary from an FGC, previously stored in its DSP external memory,
and compares it with a local binary file, diplaying the differences.
Usage:
    python bin_comp.py route/to/local/file FGC_NAME
"""

import os
import sys
import pyfgc

MEM_START = 0x80100000
MEM_JUMP = 0x80
DSP_PROP = "FGC.DEBUG.MEM.DSP"
GET_REPLY_SIZE_BYTES = 128
OUTPUT_FILE = "fgc_dump.bin"

def write_bytes(bfh, data, mem_pos):
    mem_pos -= MEM_START
    new_line = "\n"
    for value in data:
        bfh.write(f"{mem_pos:08x}:{value.split('0x')[1]}{new_line}")
        mem_pos += 4


def read_fgc_mem(fgc, bin_size):
    written_bytes = 0
    with pyfgc.fgcs(fgc, "sync") as fgc:
        with open(OUTPUT_FILE, "w") as fh:
            for mem_pos in range(MEM_START, MEM_START + bin_size, MEM_JUMP):
                pyfgc.set(DSP_PROP, mem_pos)
                partial_bin = pyfgc.get(DSP_PROP)

                # We receive something in this format: exp_value:hex_value, exp_value:hex_value, ...
                hex_values = [value.split(":")[1] for value in partial_bin.value.split(",")]
                write_bytes(fh, hex_values, mem_pos)
                written_bytes += GET_REPLY_SIZE_BYTES

            # once we finished, remove excess bytes
            # excess_bytes = written_bytes - bin_size
            # fh.seek(-excess_bytes, os.SEEK_END)
            # fh.truncate()
    
    file_size = os.stat(OUTPUT_FILE).st_size
    print(f"Dump file has size: {file_size}")


def read_file_data(file_name):
    file_lines = list()
    with open(file_name, "rb") as bfh:
        file_lines = bfh.readlines()

    statinfo  = os.stat(file_name)
    return file_lines, statinfo.st_size

if __name__ == "__main__":
    try:
        local_file = sys.argv[1]
        fgc_name   = sys.argv[2]
    
    except IndexError:
        print(__doc__)

    else:
        file_data, file_size = read_file_data(local_file)
        read_fgc_mem(fgc_name, file_size)

