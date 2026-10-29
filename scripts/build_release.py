#!/usr/bin/env python3
"""Build or verify the public file inventory without including ignored local state."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others",
                             "--exclude-standard", "-z"], capture_output=True, text=True, check=True)
    files = {}
    for name in sorted(set(result.stdout.split("\0")) - {"", "release-files.json"}):
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError(f"release file must remain inside the repository: {name}")
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    actual = inventory()
    target = ROOT / "release-files.json"
    if args.check:
        if not target.is_file() or json.loads(target.read_text()) != actual:
            parser.error("release-files.json is stale; run python3 scripts/build_release.py")
    else:
        target.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
    print(f"{'Verified' if args.check else 'Inventoried'} {len(actual)} public release files.")


if __name__ == "__main__":
    main()
