try:
    import cupy as xp
    HAS_GPU = True
except ImportError:
    import numpy as xp
    HAS_GPU = False
import multiprocessing as mp
import psutil
import os
import torch
import numba
from numba import njit
@njit(fastmath=True)
def crank_performance():
    """Forces CPU affinity and GPU max-clock settings."""
    proc = psutil.Process()
    proc.cpu_affinity(list(range(psutil.cpu_count())))
    os.system("nvidia-smi -pm 1") 
    os.system("nvidia-smi -lgc 1500,1800") # Lock core clock range
    numba.set_num_threads(psutil.cpu_count())
if __name__ == "__main__":
    crank_performance()
