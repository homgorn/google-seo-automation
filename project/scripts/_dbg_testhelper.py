import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"


def run(script, *args, env_extra=None):
    env = os.environ.copy()
    env.pop("GSC_SITE_URL", None)
    env["ALLOW_MUTATIONS"] = "0"
    if env_extra:
        env.update(env_extra)
    print("DEBUG env ALLOW_MUTATIONS =", repr(env.get("ALLOW_MUTATIONS")))
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60, cwd=PROJECT_ROOT, env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


code, out = run(
    "ads_automation.py", "--step", "S07", "--activate",
    env_extra={"ALLOW_MUTATIONS": "1"},
)
print("rc:", code)
print("out:", out[:400])
