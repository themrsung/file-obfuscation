"""Test 2 -- manual decrypt (round trip).

Encrypts every sample file individually, then decrypts each blob back through
the obfus.py CLI and compares sha256 against the original. Self-contained:
it performs its own encrypt step so it can run without test 1.

Checks per file:
  - brute-force decrypt succeeds (the discarded key is recoverable)
  - recovered bytes are identical to the original

Output: .filetest/manual-dec/{enc,out}/
"""

from _common import SAMPLES, digest, fresh, report, require_layout, sample_files, sh


def main() -> None:
    require_layout()
    root = fresh("manual-dec")
    enc_root, out_root = root / "enc", root / "out"
    checks = 0

    for src in sample_files():
        rel = src.relative_to(SAMPLES)

        blob = enc_root / rel.with_name(rel.name + ".obfus")
        blob.parent.mkdir(parents=True, exist_ok=True)
        sh("obfus.py", "-i", src, "-o", blob)

        back = out_root / rel
        back.parent.mkdir(parents=True, exist_ok=True)
        sh("obfus.py", "-i", blob, "-o", back)

        assert back.is_file(), f"no output produced for {rel}"
        checks += 1

        want, got = digest(src), digest(back)
        assert want == got, (
            f"{rel}: round trip corrupted the file\n"
            f"  original  {want}\n  recovered {got}"
        )
        checks += 1

        print(f"  ok  {rel}  ({src.stat().st_size} bytes, sha {want[:12]})")

    report("test_2_manual_decrypt", checks)


if __name__ == "__main__":
    main()
