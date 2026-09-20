"""Test 3 -- bulk encrypt (whole directory).

Runs obfus_bulk.py over .filesamples/ in one shot and verifies the output tree
replicates the input structure exactly.

Checks:
  - every input directory exists in the output (structure replicated)
  - one output file per input file, same relative path + .obfus
  - no stray or missing entries in either direction
  - each blob is plaintext length + len(MAGIC)

Output: .filetest/bulk-enc/
"""

from _common import BULK, MAGIC_LEN, SAMPLES, fresh, report, require_layout, sh


def main() -> None:
    require_layout()
    out_root = fresh("bulk-enc")

    proc = sh(BULK.name, "-i", SAMPLES, "-o", out_root)
    print(proc.stdout.rstrip())
    checks = 0

    # Directory structure replicated.
    want_dirs = {str(p.relative_to(SAMPLES))
                 for p in SAMPLES.rglob("*") if p.is_dir()}
    got_dirs = {str(p.relative_to(out_root))
                for p in out_root.rglob("*") if p.is_dir()}
    assert want_dirs <= got_dirs, (
        f"missing directories in output: {sorted(want_dirs - got_dirs)}"
    )
    checks += 1
    print(f"  ok  {len(want_dirs)} directories replicated")

    # File-for-file correspondence.
    want = {str(p.relative_to(SAMPLES)) + ".obfus"
            for p in SAMPLES.rglob("*") if p.is_file()}
    got = {str(p.relative_to(out_root))
           for p in out_root.rglob("*") if p.is_file()}

    assert not (want - got), f"missing outputs: {sorted(want - got)}"
    checks += 1
    assert not (got - want), f"unexpected extra outputs: {sorted(got - want)}"
    checks += 1
    print(f"  ok  {len(want)} files encrypted, no strays")

    # Sizes line up.
    for src in sorted(p for p in SAMPLES.rglob("*") if p.is_file()):
        rel = src.relative_to(SAMPLES)
        blob = out_root / rel.with_name(rel.name + ".obfus")
        assert blob.stat().st_size == src.stat().st_size + MAGIC_LEN, (
            f"{rel}: size mismatch "
            f"({blob.stat().st_size} vs {src.stat().st_size} + {MAGIC_LEN})"
        )
        checks += 1
    print(f"  ok  all {len(want)} blob sizes correct")

    report("test_3_bulk_encrypt", checks)


if __name__ == "__main__":
    main()
