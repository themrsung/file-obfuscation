"""Test 1 -- manual encrypt.

Encrypts every file in .filesamples/ one at a time through the obfus.py CLI
and verifies each blob individually.

Checks per file:
  - the CLI writes the requested output
  - ciphertext length == plaintext length + len(MAGIC)
  - ciphertext differs from plaintext (nonempty inputs)
Plus: encrypting one file many times yields more than one distinct
      ciphertext, because the 4-bit key is random and discarded.

Output: .filetest/manual-enc/  (mirrors the sample tree)
"""

from _common import MAGIC_LEN, SAMPLES, fresh, report, require_layout, sample_files, sh


def main() -> None:
    require_layout()
    out_root = fresh("manual-enc")
    checks = 0

    for src in sample_files():
        rel = src.relative_to(SAMPLES)
        dst = out_root / rel.with_name(rel.name + ".obfus")
        dst.parent.mkdir(parents=True, exist_ok=True)

        sh("obfus.py", "-i", src, "-o", dst)

        assert dst.is_file(), f"no output produced for {rel}"
        checks += 1

        plain, blob = src.read_bytes(), dst.read_bytes()
        assert len(blob) == len(plain) + MAGIC_LEN, (
            f"{rel}: expected {len(plain) + MAGIC_LEN} bytes, got {len(blob)}"
        )
        checks += 1

        if plain:
            assert blob[MAGIC_LEN:] != plain, f"{rel}: ciphertext body equals plaintext"
            checks += 1

        print(f"  ok  {rel}  ({len(plain)} -> {len(blob)})")

    # Random-key property. Two runs are not enough: with a 4-bit key they
    # collide 1 time in KEYSPACE (~6%), which would make this flaky. Encrypt
    # repeatedly instead and require more than one distinct ciphertext --
    # all RUNS results matching has probability KEYSPACE ** -(RUNS - 1).
    RUNS = 24
    probe = max(sample_files(), key=lambda p: p.stat().st_size)
    seen = set()
    for i in range(RUNS):
        tmp = out_root / f"_probe_{i}"
        sh("obfus.py", "-i", probe, "-o", tmp)
        seen.add(tmp.read_bytes())
        tmp.unlink()

    assert len(seen) > 1, (
        f"{RUNS} encryptions of {probe.name} produced identical bytes "
        f"-- key is not random"
    )
    checks += 1
    print(f"  ok  random-key check on {probe.name} "
          f"({len(seen)} distinct ciphertexts in {RUNS} runs)")

    report("test_1_manual_encrypt", checks)


if __name__ == "__main__":
    main()
