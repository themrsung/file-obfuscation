"""Test 4 -- bulk decrypt (whole directory round trip).

Encrypts .filesamples/ to a scratch tree, then runs obfus-bulk.py back over
that tree and compares the result to the originals. Self-contained: it does
its own encrypt pass so it can run without test 3.

Checks:
  - the recovered tree has exactly the same relative paths as .filesamples/
  - every file matches the original byte for byte (sha256)
  - the directory structure survives both hops

Output: .filetest/bulk-dec/{enc,out}/
"""

from _common import BULK, SAMPLES, fresh, report, require_layout, sh, tree


def main() -> None:
    require_layout()
    root = fresh("bulk-dec")
    enc_root, out_root = root / "enc", root / "out"
    checks = 0

    sh(BULK.name, "-i", SAMPLES, "-o", enc_root)
    proc = sh(BULK.name, "-i", enc_root, "-o", out_root)
    print(proc.stdout.rstrip())

    want, got = tree(SAMPLES), tree(out_root)

    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    assert not missing, f"missing after round trip: {missing}"
    checks += 1
    assert not extra, f"unexpected extra files: {extra}"
    checks += 1
    print(f"  ok  {len(want)} paths match the source tree")

    # Directory structure survived both hops.
    want_dirs = {str(p.relative_to(SAMPLES))
                 for p in SAMPLES.rglob("*") if p.is_dir()}
    got_dirs = {str(p.relative_to(out_root))
                for p in out_root.rglob("*") if p.is_dir()}
    assert want_dirs <= got_dirs, (
        f"directories lost in round trip: {sorted(want_dirs - got_dirs)}"
    )
    checks += 1
    print(f"  ok  {len(want_dirs)} directories replicated")

    bad = [p for p in want if want[p] != got[p]]
    assert not bad, "content changed in round trip:\n" + "\n".join(
        f"  {p}\n    want {want[p]}\n    got  {got[p]}" for p in bad
    )
    checks += len(want)
    print(f"  ok  all {len(want)} files byte-identical to the originals")

    report("test_4_bulk_decrypt", checks)


if __name__ == "__main__":
    main()
