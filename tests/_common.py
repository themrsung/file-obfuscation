"""Shared helpers for the obfus test scripts.

Every test writes exclusively inside .filetest/ (gitignored scratch space)
and reads .filesamples/ read-only.
"""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / ".filesamples"
SCRATCH = ROOT / ".filetest"

OBFUS = ROOT / "obfus.py"
BULK = ROOT / "obfus_bulk.py"

MAGIC_LEN = 6  # len(obfus.MAGIC)


def sh(*args: str | Path) -> subprocess.CompletedProcess:
    """Run a CLI command, capturing output; raises on non-zero exit."""
    proc = subprocess.run(
        [sys.executable, *[str(a) for a in args]],
        cwd=ROOT, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"command failed ({proc.returncode}): {' '.join(str(a) for a in args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(root: Path) -> dict[str, str]:
    """Relative path -> sha256, for every file under root."""
    return {
        str(p.relative_to(root)): digest(p)
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def fresh(name: str) -> Path:
    """An empty scratch dir under .filetest/, wiped if it already exists."""
    d = SCRATCH / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    return d


def sample_files() -> list[Path]:
    files = sorted(p for p in SAMPLES.rglob("*") if p.is_file())
    if not files:
        raise AssertionError(f"no sample files found under {SAMPLES}")
    return files


def require_layout() -> None:
    if not SAMPLES.is_dir():
        raise AssertionError(f"missing samples directory: {SAMPLES}")
    SCRATCH.mkdir(exist_ok=True)


def report(name: str, checks: int) -> None:
    print(f"\nPASS  {name}  ({checks} checks)")
