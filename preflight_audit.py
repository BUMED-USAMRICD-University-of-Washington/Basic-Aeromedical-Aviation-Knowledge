import telemetry_link
from telemetry_link import time_manager
import os
import datetime
now = time_manager.get_now()
from astropy.time import Time
import ast
def run_diagnostics(directory="."):
    print("===========================================================")
    print("  AVIONICS DIAGNOSTIC: SCANNING FOR STUBS AND TRUNCATIONS  ")
    print("===========================================================\n")
    suspicious_files = []
    files_scanned = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                files_scanned += 1              
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.split('\n')              
                        issues = []
                        try:
                            ast.parse(content)
                        except SyntaxError as e:
                            issues.append(f"CRITICAL: Syntax Error. File may be cut off mid-way. (Line {e.lineno})")
                        pass_count = content.split().count('pass')
                        if pass_count >= 3:
                            issues.append(f"WARNING: Contains {pass_count} 'pass' statements. Logic may be stubbed out.")               
                        if "TODO" in content or "FIXME" in content:
                            issues.append("NOTE: Contains 'TODO' or 'FIXME' developer notes.")
                        if len(lines) < 8 and not file.startswith('__init__'):
                            issues.append(f"WARNING: File is suspiciously short ({len(lines)} lines).")
                        if issues:
                            suspicious_files.append((filepath, issues))
                except UnicodeDecodeError:
                    pass # Skip non-text files
    if not suspicious_files:
        print(f"[SYSTEM GREEN] Scanned {files_scanned} files.")
        print("No cut-off files or obvious stubs detected. Your physics engines are structurally intact.")
    else:
        print(f"[SYSTEM YELLOW] Scanned {files_scanned} files.")
        print(f"Found {len(suspicious_files)} files that require pilot inspection:\n")
        for filepath, issues in suspicious_files:
            print(f"-> {filepath}")
            for issue in issues:
                print(f"   * {issue}")
            print()
if __name__ == "__main__":
    run_diagnostics()
