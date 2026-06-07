import sys
import psutil # Ensure this is installed via pip
from collections import OrderedDict

class DynamicMemoryCache:
    def __init__(self, percentage=0.25):
        # Dynamically detect total system memory
        try:
            total_memory_bytes = psutil.virtual_memory().total
            self.max_size_bytes = int(total_memory_bytes * percentage)
            print(f"✅ Cache initialized: {self.max_size_bytes / (1024**3):.2f} GB allocated.")
        except Exception as e:
            # Fallback to a safe 1GB default if system access is blocked (e.g., iOS Sandbox)
            print(f"⚠️ Could not detect RAM, defaulting to 1GB: {e}")
            self.max_size_bytes = 1 * 1024 * 1024 * 1024
            
        self.cache = OrderedDict()
        self.current_size = 0

    def get(self, key):
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        # Calculate size of the new value
        item_size = sys.getsizeof(value)
        
        # Don't cache massive objects that exceed total cache size
        if item_size > self.max_size_bytes:
            return False

        # Evict oldest until space is available
        while self.current_size + item_size > self.max_size_bytes:
            oldest_key, oldest_val = self.cache.popitem(last=False)
            self.current_size -= sys.getsizeof(oldest_val)

        # Add new item
        self.cache[key] = value
        self.current_size += item_size
        return True
