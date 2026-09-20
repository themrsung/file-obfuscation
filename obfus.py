"""file-obfuscation — single-file entry point.

Encrypt: encrypt file with random key
Decrypt: decrypt file by bruteforce

args:
-i / --input FILENAME   (required; no default)
-e / --encrypt          (flag; default when input does not end in .obfus)
-d / --decrypt          (flag; default when input ends in .obfus)
-o / --output FILENAME  (defaults to "original.extension.obfus" when encrypting,
                         "original.extension" when decrypting)

-e cannot be used with -d.
Decrypting a file whose name does not end in .obfus requires an explicit -o,
since there is no suffix to strip. Output is refused if it equals the input.

The pack/unpack core lives in obfus_core.py, which is meant to be copied
rather than depended on; see the banner at the top of that file.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from obfus_core import EXT, pack, unpack  # noqa: E402


def resolve_mode(inp: Path, encrypt: bool, decrypt: bool) -> str:
    """Explicit flag wins; otherwise infer from the .obfus suffix."""
    if encrypt:
        return "encrypt"
    if decrypt:
        return "decrypt"
    return "decrypt" if inp.suffix == EXT else "encrypt"


def resolve_output(inp: Path, mode: str, output: str | None) -> Path:
    if output is not None:
        return Path(output)
    if mode == "encrypt":
        return inp.with_name(inp.name + EXT)
    if inp.suffix == EXT:
        return inp.with_name(inp.name[: -len(EXT)])
    # Nothing to strip -- a default would overwrite the input.
    raise SystemExit(
        f"obfus: cannot infer output name for decrypting {inp.name!r} "
        f"(no {EXT} suffix); pass -o/--output"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obfus",
        description="Obfuscate a file with a random discarded key; "
                    "recover it by brute force.",
    )
    p.add_argument("-i", "--input", default=None, help="input filename")
    p.add_argument("-o", "--output", default=None,
                   help=f"output filename (default: add/strip {EXT})")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("-e", "--encrypt", action="store_true",
                      help=f"force encrypt (default when input is not {EXT})")
    mode.add_argument("-d", "--decrypt", action="store_true",
                      help=f"force decrypt (default when input is {EXT})")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.input is None:
        raise SystemExit("obfus: -i/--input is required")

    inp = Path(args.input)
    if not inp.is_file():
        raise SystemExit(f"obfus: no such file: {inp}")

    mode = resolve_mode(inp, args.encrypt, args.decrypt)
    out = resolve_output(inp, mode, args.output)

    if out.resolve() == inp.resolve():
        raise SystemExit("obfus: output would overwrite the input; pass -o/--output")

    data = inp.read_bytes()
    try:
        result = pack(data) if mode == "encrypt" else unpack(data)
    except ValueError as exc:
        raise SystemExit(f"obfus: {exc}: {inp}") from exc

    if out.parent != Path(""):
        out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result)
    print(f"{mode}: {inp} -> {out} ({len(data)} -> {len(result)} bytes)")


if __name__ == "__main__":
    main()
