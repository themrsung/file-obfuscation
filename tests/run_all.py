"""Run all four obfus tests in order.

Every test runs even if an earlier one fails; the failures are collected and
reported together, and the exit status is non-zero if any of them failed.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TESTS = [
    "test_1_manual_encrypt.py",
    "test_2_manual_decrypt.py",
    "test_3_bulk_encrypt.py",
    "test_4_bulk_decrypt.py",
]


def main() -> None:
    failures = []
    for name in TESTS:
        print(f"\n{'=' * 60}\n{name}\n{'=' * 60}", flush=True)
        rc = subprocess.run([sys.executable, str(HERE / name)]).returncode
        if rc != 0:
            failures.append(name)
            print(f"FAIL  {name}", flush=True)

    print(f"\n{'=' * 60}", flush=True)
    if failures:
        print(f"{len(failures)}/{len(TESTS)} failed: {', '.join(failures)}", flush=True)
        sys.exit(1)
    print(f"all {len(TESTS)} tests passed", flush=True)


if __name__ == "__main__":
    main()
