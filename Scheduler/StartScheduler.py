import subprocess
import sys
import time

from VaultSecrets import refresh_vault_secrets


def main() -> None:
    print("Running initial Vault sync...")

    for attempt in range(1, 6):
        try:
            refresh_vault_secrets()
            print("Initial Vault sync complete.")
            break
        except Exception as error:
            print(f"Initial Vault sync failed, attempt {attempt}/5: {error}")

            if attempt == 5:
                raise

            time.sleep(5)

    print("Starting Scheduler...")
    subprocess.run([sys.executable, "/Scheduler/Scheduler.py"], check=True)


if __name__ == "__main__":
    main()