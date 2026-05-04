import subprocess
import sys

def run(script: str) -> None:
    print(f"Running {script}...")
    result = subprocess.run([sys.executable, script], check=False)

    if result.returncode != 0:
        raise SystemExit(f"{script} failed with exit code {result.returncode}")

if __name__ == "__main__":
    run("Setup_Accounts.py")
    run("Setup_SchedulerIndex_Tasks.py")
    print("MGMT setup complete.")