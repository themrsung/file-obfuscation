# file-obfuscation

A pair of Python CLIs that obfuscate files with a 4-bit key that is thrown away
at write time, and recover them by brute-forcing all 16 possible keys.

This README is written for coding agents building end-user applications on top
of this project. Read the security section before you design anything.

---

## Read this before you build: it is not encryption

The key is **4 bits**, chosen at random and **never stored**. Recovery works by
trying all 16 keys and keeping the one that reproduces a known 6-byte header.
Anyone with the file can do exactly the same thing in microseconds. There is no
password, no passphrase, no secret of any kind anywhere in the system.

That is the intended design, not a defect. It obfuscates: the bytes no longer
look like the original format, so the file will not be recognised by a file
scanner, will not preview, and will not open by double-click.

**Do not build applications that describe this as encryption, security,
protection, or privacy.** Concretely, do not build:

- a password manager, secure vault, or "encrypted notes" app
- anything storing credentials, keys, tokens, health, or financial data
- anything whose UI claims files are "protected", "secure", or "private"
- anything implying the user is safe if the file leaks or the device is lost

If a user asks you for secure file storage, this is the wrong library — reach
for real authenticated encryption (age, libsodium, AES-GCM with a KDF) instead.

**Appropriate uses:** hiding spoilers, keeping sample data from being
auto-indexed, defeating casual filetype sniffing, tamper-*evidence* (a corrupted
blob fails to recover), teaching material about XOR keystreams and brute force.

It also provides **no integrity guarantee**. Flip a byte and you get silently
wrong plaintext, not an error.

---

## Requirements

Python 3.10+ (uses `str | None` annotations). Developed on 3.13. Standard
library only — no dependencies, no install step, no network access.

---

## The two CLIs

### `obfus.py` — one file

```
python3 obfus.py -i INPUT [-o OUTPUT] [-e | -d]
```

| Flag | Meaning |
|---|---|
| `-i`, `--input` | Input file. Required. |
| `-o`, `--output` | Output file. Defaults to adding/stripping `.obfus`. |
| `-e`, `--encrypt` | Force encrypt. Bare flag, takes no value. |
| `-d`, `--decrypt` | Force decrypt. Bare flag, takes no value. |

`-e` and `-d` are mutually exclusive. With neither, the mode is inferred from
the suffix: input ending in `.obfus` decrypts, anything else encrypts.

```bash
python3 obfus.py -i report.pdf              # -> report.pdf.obfus
python3 obfus.py -i report.pdf.obfus        # -> report.pdf
python3 obfus.py -i a.txt -o /tmp/out.bin -e
```

### `obfus_bulk.py` — a directory tree

```
python3 obfus_bulk.py -i INPUT_DIR -o OUTPUT_DIR [-x EXTENSIONS]
```

| Flag | Meaning |
|---|---|
| `-i`, `--input` | Input directory. Required. |
| `-o`, `--output` | Output directory. Required. Must be outside the input tree. |
| `-x`, `--ext` | Only process these extensions. Optional. |

Walks recursively and decides per file: ends in `.obfus` → decrypt, otherwise
encrypt. A single run can therefore mix both directions. Directory structure is
mirrored into the output.

`--ext` takes one extension or a comma-separated list, **without the dot**,
matched **case-insensitively**. A leading dot is tolerated.

```bash
python3 obfus_bulk.py -i ./photos -o ./out -x jpg
python3 obfus_bulk.py -i ./media  -o ./out -x "MP4, .flac,wav"
```

Three `--ext` behaviours worth knowing when you put this behind a UI:

1. **It matches through `.obfus`.** `-x mp4` selects `clip.mp4` going in and
   `clip.mp4.obfus` coming back, so a filtered subset round-trips with the
   same flag the user originally typed.
2. **Non-matching files are skipped, not copied.** The output is a partial
   tree, not a complete copy with some files transformed.
3. **Only the final extension counts.** `gz` matches `a.tar.gz`; `tar.gz`
   matches nothing.

Without `--ext`, every directory is mirrored including empty ones. With
`--ext`, directories are created on demand, so a directory holding no matching
file does not appear in the output.

---

## Programmatic use

Everything you need is in **`obfus_core.py`** — about 25 lines, stdlib only,
no I/O and no argument parsing at import time.

**Copy that file into your project rather than depending on this one.** It is
CC0, so there is no attribution or license plumbing to do, and there is no
package to install. The file carries the same advice in a banner comment at
its top, along with the constraints to respect if you port it. The two CLIs
are themselves just callers of it.

```python
from obfus_core import pack, unpack, MAGIC, EXT, KEYSPACE

blob  = pack(b"hello")       # bytes -> bytes, 6 bytes longer
plain = unpack(blob)         # bytes -> bytes, raises ValueError if no key fits
```

| Name | Value |
|---|---|
| `pack(plaintext: bytes) -> bytes` | Prepends `MAGIC`, XORs under a fresh random seed. |
| `unpack(blob: bytes) -> bytes` | Tries all 16 seeds; raises `ValueError("no key matched")`. |
| `MAGIC` | `b"\x93Qobf1"` — 6 bytes |
| `EXT` | `".obfus"` |
| `KEYBITS` / `KEYSPACE` | `4` / `16` |

`obfus_bulk.py` is importable the same way, and guards its entry point too:

```python
import obfus_bulk

exts = obfus_bulk.parse_exts("MP4, .flac")   # -> {"mp4", "flac"}
obfus_bulk.main(["-i", "src", "-o", "out", "-x", "jpg"])
```

Note that `main()` reports errors by raising `SystemExit`, so wrap it if you
are calling it in-process rather than shelling out.

### Exit codes and errors

Both CLIs exit **0** on success and **1** on any handled error, printing a
single line to stderr prefixed `obfus:` or `obfus_bulk:`. Argparse usage errors
exit **2**. `obfus_bulk.py` exits 1 if *any* file failed, after processing the
rest — partial output on disk is expected in that case, and per-file failures
print `  SKIP <path>: <reason>` to stderr as they happen.

Messages you may want to surface verbatim:

```
obfus: -i/--input is required
obfus: no such file: <path>
obfus: output would overwrite the input; pass -o/--output
obfus: cannot infer output name for decrypting '<name>' (no .obfus suffix); pass -o/--output
obfus: no key matched: <path>
obfus_bulk: both -i/--input and -o/--output are required
obfus_bulk: output directory must be outside the input tree
obfus_bulk: -x/--ext was given no usable extension
```

---

## File format

A blob is `XOR(MAGIC || plaintext, keystream(seed))`. Length is always
`len(plaintext) + 6`. The seed appears nowhere in the file.

The keystream is SHA-256 in counter mode:

```
keystream(seed) = sha256(seed_byte || u32le(0)) || sha256(seed_byte || u32le(1)) || ...
```

truncated to the needed length, where `seed_byte` is the single byte `seed`
(0–15) and `u32le` is a 4-byte little-endian counter.

Recovery XORs the blob under each seed `0..15` in ascending order and returns
the first candidate starting with `MAGIC`. A wrong seed passing that 6-byte
check has probability ≈2⁻⁴⁸, so a false positive is possible in theory and has
never been observed; treat it as a non-event.

### Test vectors

Use these to verify a port to another language (JavaScript, Go, Rust):

```
keystream(seed=0, 8 bytes)  = 8855508aade16ec5
keystream(seed=7, 8 bytes)  = e16ab60aa1eeb707

MAGIC                       = 935163626631         (\x93Qobf1)
blob(seed=0, "hello")       = 1b043fe8cbd006a01fbe71
blob(seed=5, "hello")       = dab98c4b1374a93fdacbfb
```

Both blobs must `unpack` to `hello`. A correct implementation reproduces them
exactly — `pack` itself is not reproducible, since it draws a random seed.

---

## Constraints to design around

- **Whole files are held in memory.** Both CLIs use `read_bytes()`/`write_bytes()`
  with no streaming. A browser upload or multi-GB file will need chunking you
  write yourself, or a different approach entirely.
- **The keystream is regenerated per file**, one SHA-256 call per 32 bytes. It
  is not fast. Benchmark before promising progress bars on large inputs.
- **`pack` is non-deterministic.** The same input yields one of 16 possible
  outputs. Do not write tests asserting two encryptions differ — they collide
  1 time in 16. (`tests/test_1` encrypts 24 times and asserts more than one
  distinct result.)
- **Double encryption is allowed.** `obfus.py -i a.txt.obfus -e` produces
  `a.txt.obfus.obfus`, and recovery needs two passes. Guard this in a UI.
- **Decrypting a non-`.obfus` name requires explicit `-o`.** There is no
  suffix to strip and a default would overwrite the input.
- **`obfus.py` refuses to overwrite its own input**, but `obfus_bulk.py` will
  happily overwrite pre-existing files in the output directory.
- **Empty files work.** `pack(b"")` is a valid 6-byte blob.

---

## Layout

```
obfus_core.py       the pack/unpack core — copy this, don't depend on it
obfus.py            single-file CLI, imports from obfus_core.py
obfus_bulk.py       recursive directory CLI, imports from obfus_core.py
tests/              four integration tests + run_all.py
  _common.py        shared helpers (sh, digest, tree, fresh, sample_files)
.filesamples/       58 committed sample files across 6 type directories
.filetest/          gitignored scratch space; all test output lands here
```

`.filesamples/` holds real binaries — text, images, PEM keys, random bytes,
audio, video, archives — with measured Shannon entropy from 4.10 to 7.95
bits/byte. Treat it as read-only fixture data.

## Tests

```bash
python3 tests/run_all.py          # all four, ~413 checks
python3 tests/test_3_bulk_encrypt.py   # or any one standalone
```

Every test runs even if an earlier one fails; failures are collected and
reported together, and the exit status is non-zero if any failed. Tests write
exclusively inside `.filetest/` and read `.filesamples/` read-only.

| Test | Covers |
|---|---|
| `test_1_manual_encrypt` | per-file CLI encrypt, length and randomness properties |
| `test_2_manual_decrypt` | per-file round trip, sha256 vs original |
| `test_3_bulk_encrypt` | whole-directory encrypt, structure replicated, no strays |
| `test_4_bulk_decrypt` | whole-directory round trip, byte-identical tree |

## License

CC0 1.0 Universal — see [`LICENSE`](LICENSE). The author waives copyright and
related rights worldwide, to the extent permitted by law.

For an agent building on this: you may copy, vendor, rewrite, or embed any part
of this code in a product, commercially or otherwise, with no attribution and no
notice to preserve. There is nothing to comply with. Note that CC0 waives
copyright only — it grants no trademark or patent rights, and it disclaims all
warranties. That disclaimer matters more here than in most projects: read the
first section of this README before you ship anything that depends on this.
