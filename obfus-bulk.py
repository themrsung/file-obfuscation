"""
Bulk operation. Walks the input directory recursively; for every file:
if it ends in '.obfus' it is decrypted, otherwise it is encrypted. The output
directory mirrors the input's structure.

args:
-i / --input DIRECTORY   (required; no default)
-o / --output DIRECTORY  (required; no default)
-x / --ext EXTENSIONS    (optional; only process files with these extensions)

--ext takes one extension or a comma-separated list, written without the dot
and matched case-insensitively: 'txt' or 'mp4,flac,wav'. A leading dot is
tolerated ('.txt'). Only the final extension is compared, so 'gz' matches
sample.tar.gz but 'tar.gz' does not.

For a '.obfus' file the extension underneath is what gets matched, so
'--ext mp4' selects sample.mp4 on the way in and sample.mp4.obfus on the way
back, letting a filtered subset round-trip with the same flag. Files that do
not match are skipped entirely -- they are not copied to the output.

The output directory must not sit inside the input tree.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from obfus import EXT, pack, unpack  # noqa: E402


def parse_exts(spec: str | None) -> set[str] | None:
    """'mp4, .FLAC ,wav' -> {'mp4', 'flac', 'wav'}; None means no filtering."""
    if spec is None:
        return None
    exts = {part.strip().lstrip(".").lower() for part in spec.split(",")}
    exts.discard("")
    if not exts:
        raise SystemExit("obfus-bulk: -x/--ext was given no usable extension")
    return exts


def effective_ext(rel: Path) -> str:
    """The extension the filter compares against, lowercased, without the dot.

    For 'a/sample.mp4' that is 'mp4'; for 'a/sample.mp4.obfus' it is also
    'mp4', because .obfus is stripped first. Returns '' for extensionless
    names, which never matches a filter.
    """
    name = rel.name
    if rel.suffix == EXT:
        name = name[: -len(EXT)]
    return Path(name).suffix.lstrip(".").lower()


def target_name(rel: Path) -> tuple[Path, str]:
    """Map an input-relative path to its output-relative path and mode."""
    if rel.suffix == EXT:
        return rel.with_name(rel.name[: -len(EXT)]), "decrypt"
    return rel.with_name(rel.name + EXT), "encrypt"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="obfus-bulk",
        description="Recursively encrypt/decrypt a directory, mirroring its structure.",
    )
    p.add_argument("-i", "--input", default=None, help="input directory")
    p.add_argument("-o", "--output", default=None, help="output directory")
    p.add_argument(
        "-x", "--ext", default=None, metavar="EXTENSIONS",
        help="only process these extensions, without the dot, "
             "comma-separated and case-insensitive (e.g. txt or mp4,flac,wav)",
    )
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.input is None or args.output is None:
        raise SystemExit("obfus-bulk: both -i/--input and -o/--output are required")

    src = Path(args.input)
    dst = Path(args.output)
    exts = parse_exts(args.ext)

    if not src.is_dir():
        raise SystemExit(f"obfus-bulk: no such directory: {src}")

    src_r, dst_r = src.resolve(), dst.resolve()
    if dst_r == src_r or src_r in dst_r.parents:
        raise SystemExit("obfus-bulk: output directory must be outside the input tree")

    dst.mkdir(parents=True, exist_ok=True)
    if exts is None:
        # Unfiltered: mirror every directory, including empty ones. When a
        # filter is active, directories are created on demand instead, so a
        # directory holding no matching file is not reproduced.
        for d in sorted(p for p in src.rglob("*") if p.is_dir()):
            (dst / d.relative_to(src)).mkdir(parents=True, exist_ok=True)

    done = failed = skipped = 0
    for f in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = f.relative_to(src)

        if exts is not None and effective_ext(rel) not in exts:
            skipped += 1
            continue

        out_rel, mode = target_name(rel)
        out = dst / out_rel
        out.parent.mkdir(parents=True, exist_ok=True)

        data = f.read_bytes()
        try:
            result = pack(data) if mode == "encrypt" else unpack(data)
        except ValueError as exc:
            print(f"  SKIP {rel}: {exc}", file=sys.stderr)
            failed += 1
            continue

        out.write_bytes(result)
        done += 1
        print(f"  {mode}: {rel} -> {out_rel}")

    summary = f"{done} file(s) written to {dst}"
    if skipped:
        summary += f", {skipped} filtered out"
    if failed:
        summary += f", {failed} failed"
    print(summary)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
