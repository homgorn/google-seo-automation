import os
import subprocess
import sys

env = os.environ.copy()
env["ALLOW_MUTATIONS"] = "1"
print("parent env value:", env.get("ALLOW_MUTATIONS"))

code = "import os; print('child sees:', os.environ.get('ALLOW_MUTATIONS'))"
proc = subprocess.run(
    [sys.executable, "-c", code], capture_output=True, text=True, env=env
)
print(proc.stdout.strip(), proc.stderr.strip())

# Теперь через сам скрипт
proc2 = subprocess.run(
    [sys.executable, "scripts/ads_automation.py", "--step", "S07", "--activate"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
)
print("rc:", proc2.returncode)
print(proc2.stdout.strip())
