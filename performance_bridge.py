# control_bridge/performance_bridge.py
import os
import psutil
import torch # If utilizing CUDA for matrix math
import numba

def crank_performance():
    """Forces CPU affinity and GPU max-clock settings."""
    # 1. CPU: Pin process to high-performance cores (assuming a standard high-end multicore layout)
    proc = psutil.Process()
    # Pin to cores 0 through (Total Cores - 1)
    proc.cpu_affinity(list(range(psutil.cpu_count())))
    
    # 2. GPU: Set to "Performance Mode" (NVIDIA-SMI integration)
    # This forces the card to ignore power-saving states
    os.system("nvidia-smi -pm 1") 
    os.system("nvidia-smi -lgc 1500,1800") # Lock core clock range
    
    # 3. NUMBA: Force compilation to use all cores
    numba.set_num_threads(psutil.cpu_count())

# Add this to the very beginning of your main app boot
if __name__ == "__main__":
    crank_performance()
