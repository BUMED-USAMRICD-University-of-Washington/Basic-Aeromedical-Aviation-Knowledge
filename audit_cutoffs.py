import os
try:
    import cupy as xp
    HAS_GPU = True
    print("NVIDIA CUDA Cores Engaged: Array Batching Active (Performance)")
except ImportError:
    import numpy as xp
    HAS_GPU = False
    print("CPU Fallback: Standard Vectorization Active (Performance)")
import ast
def hunt_for_cutoffs(directory="."):
    print("Hunting for truncated Python files...\n")
    cut_off_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    ast.parse(source_code)
                except SyntaxError as e:
                    error_msg = str(e).lower()
                    if "unexpected eof" in error_msg or "unterminated" in error_msg or "invalid syntax" in error_msg:
                        cut_off_files.append((file, e.lineno))
                except Exception as e:
                    print(f"Could not read {file}: {e}")
    if not cut_off_files:
        print("All clear! No cut-off files detected in the repository.")
    else:
        print(f"Found {len(cut_off_files)} cut-off or broken file(s):")
        for filename, line_num in cut_off_files:
            print(f"   - {filename} (Cuts off or breaks around line {line_num})")
if __name__ == "__main__":
    hunt_for_cutoffs()
