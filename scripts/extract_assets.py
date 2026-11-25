#!/usr/bin/env python3
"""Extract offline gameplay assets from the frozen original JustPiano APK.

Keeps copyrighted assets strictly out of Git (extracted into .gitignore-shielded
directories under src/app/src/main/assets/). Never modifies raw/JustPiano.apk.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_APK_SHA256 = "fccf7ee9816601f4833d5bb5a2419cfd3fa9782c6dfda3003d4cc2b9781f9d66"

# Offline gameplay asset prefixes inside the APK -> expected file counts (Phase 0 audit)
ASSET_GROUPS: dict[str, tuple[str, int]] = {
    "songs": ("assets/songs/", 4801),
    "sound": ("assets/sound/", 77),
    "drawable": ("assets/drawable/", 59),
    "mod": ("assets/mod/", 189),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_resolve_target(base_dir: Path, rel_path: str) -> Path:
    if not rel_path or "\\" in rel_path:
        raise RuntimeError(f"Unsafe ZIP entry path rejected: {rel_path!r}")
    posix_rel = PurePosixPath(rel_path)
    if posix_rel.is_absolute() or any(part in ("", ".", "..") for part in posix_rel.parts):
        raise RuntimeError(f"Unsafe ZIP entry path traversal blocked: {rel_path!r}")

    base_resolved = base_dir.resolve()
    target = (base_resolved / Path(*posix_rel.parts)).resolve()
    try:
        rel_resolved = target.relative_to(base_resolved)
    except ValueError as exc:
        raise RuntimeError(f"Unsafe ZIP entry path escape blocked: {rel_path!r}") from exc
    if target == base_resolved or not rel_resolved.parts:
        raise RuntimeError(f"Unsafe ZIP entry resolves to base directory: {rel_path!r}")
    return target


def extract_assets(
    apk_path: Path,
    out_assets_dir: Path,
    selected_groups: list[str],
    *,
    check_only: bool,
    clean: bool,
    skip_hash: bool,
) -> int:
    selected_groups = list(dict.fromkeys(selected_groups))

    if not apk_path.is_file():
        print(f"[ERROR] Original APK not found: {apk_path}", file=sys.stderr)
        print("        Place the frozen original APK at raw/JustPiano.apk first.", file=sys.stderr)
        return 1

    try:
        actual_hash = sha256_file(apk_path)
    except OSError as exc:
        print(f"[ERROR] Failed to read APK: {exc}", file=sys.stderr)
        return 1

    if skip_hash:
        print(f"[WARN] SHA-256 verification skipped (actual: {actual_hash})")
    elif actual_hash != EXPECTED_APK_SHA256:
        print("[ERROR] APK SHA-256 mismatch!", file=sys.stderr)
        print(f"        Expected: {EXPECTED_APK_SHA256}", file=sys.stderr)
        print(f"        Actual:   {actual_hash}", file=sys.stderr)
        return 2
    else:
        print(f"[OK] APK SHA-256 verified: {actual_hash}")

    counts: dict[str, int] = {g: 0 for g in selected_groups}
    total_bytes = 0

    try:
        with zipfile.ZipFile(apk_path, "r") as zf:
            entries_to_extract: list[tuple[zipfile.ZipInfo, Path]] = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                for group in selected_groups:
                    prefix, _ = ASSET_GROUPS[group]
                    if info.filename.startswith(prefix):
                        rel_under_assets = info.filename[len("assets/") :]
                        target = safe_resolve_target(out_assets_dir, rel_under_assets)
                        entries_to_extract.append((info, target))
                        counts[group] += 1
                        total_bytes += info.file_size
                        break

            count_mismatch = False
            for group in selected_groups:
                _, expected_count = ASSET_GROUPS[group]
                actual_count = counts[group]
                status = "OK" if actual_count == expected_count else "WARN"
                if actual_count != expected_count:
                    count_mismatch = True
                print(f"[{status}] group={group:<8} files={actual_count} (expected={expected_count})")

            if count_mismatch and not skip_hash:
                print("[ERROR] Asset group count mismatch against Phase 0 baseline.", file=sys.stderr)
                return 3

            if check_only:
                print(
                    f"[DRY-RUN] Verified {len(entries_to_extract)} files "
                    f"({total_bytes:,} bytes). No files written."
                )
                return 0

            # Clean only after archive, counts, and all target paths are validated.
            if clean:
                for group in selected_groups:
                    group_dir = out_assets_dir / group
                    if group_dir.exists():
                        shutil.rmtree(group_dir)
                        print(f"[CLEAN] Removed {group_dir}")

            out_assets_dir.mkdir(parents=True, exist_ok=True)
            for info, target in entries_to_extract:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    except (zipfile.BadZipFile, RuntimeError, OSError) as exc:
        print(f"[ERROR] Extraction failed: {exc}", file=sys.stderr)
        return 4

    print(
        f"[DONE] Extracted {len(entries_to_extract)} offline asset files "
        f"({total_bytes:,} bytes) -> {out_assets_dir}"
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Verify raw/JustPiano.apk SHA-256 and extract offline assets for local Gradle builds."
    )
    parser.add_argument(
        "--apk",
        type=Path,
        default=repo_root / "raw" / "JustPiano.apk",
        help="Path to frozen original APK (default: raw/JustPiano.apk)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "src" / "app" / "src" / "main" / "assets",
        help="Output assets directory (default: src/app/src/main/assets)",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        choices=list(ASSET_GROUPS.keys()),
        default=list(ASSET_GROUPS.keys()),
        help="Asset groups to extract (default: songs sound drawable mod)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify APK hash, target paths, and asset counts without writing any files",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing target group folders after validation, before extracting",
    )
    parser.add_argument(
        "--skip-hash",
        action="store_true",
        help="Skip SHA-256 and baseline count enforcement (not recommended)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return extract_assets(
        apk_path=args.apk,
        out_assets_dir=args.out,
        selected_groups=args.groups,
        check_only=args.check,
        clean=args.clean,
        skip_hash=args.skip_hash,
    )


if __name__ == "__main__":
    raise SystemExit(main())
