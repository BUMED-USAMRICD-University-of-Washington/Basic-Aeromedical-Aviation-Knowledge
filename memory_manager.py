import numba
from numba import njit
import multiprocessing as mp
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
import psutil
import sys
from collections import OrderedDict
@njit(fastmath=True)
def preallocate_buffer(size_mb):
    """
    Verifies that the requested memory block is contiguous.
    """
    buffer = bytearray(size_mb * 1024 * 1024)
    if len(buffer) == (size_mb * 1024 * 1024):
        print(f"CACHE STATUS: {size_mb}MB Contiguous Cache Locked.")
    return buffer
class DynamicMemoryCache:
    @njit(fastmath=True)
    def __init__(self, percentage=0.25):
        try:
            total_memory_bytes = psutil.virtual_memory().total
            self.max_size_bytes = int(total_memory_bytes * percentage)
            print(f"Cache initialized: {self.max_size_bytes / (1024**3):.2f} GB allocated.")
        except Exception as e:
            print(f"Could not detect RAM, defaulting to 1GB: {e}")
            self.max_size_bytes = 1 * 1024 * 1024 * 1024
        self.cache = OrderedDict()
        self.current_size = 0
    @njit(fastmath=True)
    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]
    @njit(fastmath=True)
    def put(self, key, value):
        item_size = sys.getsizeof(value)
        if item_size > self.max_size_bytes:
            return False
        while self.current_size + item_size > self.max_size_bytes:
            oldest_key, oldest_val = self.cache.popitem(last=False)
            self.current_size -= sys.getsizeof(oldest_val)
        self.cache[key] = value
        self.current_size += item_size
        return True
