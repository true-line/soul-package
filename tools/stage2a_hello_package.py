#!/usr/bin/env python3
"""Build and check the controlled hello.soul transport candidate."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tarfile


SOURCE_COMMIT = "8e82f47781e583e4b09352cbfef5ca3bfefe45aa"
TEMPLATE = "templates/hello.soul"
DEFINITION_DOMAIN = b"agent-bot/stage2a-definition-opt-closure/v1\0"
BLOCK = tarfile.BLOCKSIZE
DIRECTORIES = ("Contents", "Contents/opt", "Contents/primitives")
FILES = (
    "Contents/SoulInfo.json",
    "Contents/SoulLock.json",
    "Contents/opt/quickstart-adapter.mjs",
    "Contents/opt/quickstart-check.mjs",
    "Contents/primitives/quickstart-task.json",
)
SEEDS = (
    "Contents/workspaces/scratch/answer.txt",
    "Contents/workspaces/scratch/issue.md",
)
INVENTORY = tuple(sorted((*DIRECTORIES, *FILES)))
STOCK_SOURCE_COMMIT = "068f5dd4d6f17691e66ea6cb3d126a0e40971f9a"
STOCK_TEMPLATE = "templates/stage2a-stock-hello.soul"
STOCK_FILES = (
    "Contents/SoulInfo.json",
    "Contents/SoulLock.json",
    "Contents/opt/stock-claude.json",
    "Contents/primitives/qualification-task.json",
)


@dataclass(frozen=True)
class Profile:
    name: str
    source_commit: str
    template: str
    files: tuple[str, ...]
    seeds: tuple[str, ...]

    @property
    def inventory(self):
        return tuple(sorted((*DIRECTORIES, *self.files)))


ORIGINAL = Profile("original", SOURCE_COMMIT, TEMPLATE, FILES, SEEDS)
STOCK = Profile("stock-claude-v1", STOCK_SOURCE_COMMIT, STOCK_TEMPLATE, STOCK_FILES, ())
PROFILES = {profile.name: profile for profile in (ORIGINAL, STOCK)}
SHA256 = re.compile(r"[0-9a-f]{64}")
SOUL_ID = re.compile(r"agent_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
MAX_FILE_BYTES = 256 << 20
MAX_TOTAL_BYTES = 1 << 30


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_records(records):
    # The fixed record keys, paths, modes and digests are ASCII. The only
    # numbers are nonnegative integers below the JCS safe-integer bound.
    return json.dumps(records, sort_keys=True, separators=(",", ":")).encode("ascii")


def definition_measurement(records):
    return "sha256:" + sha256(DEFINITION_DOMAIN + canonical_records(records))


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def load_json(data):
    def invalid_constant(value):
        raise ValueError(f"non-JSON number: {value}")

    return json.loads(
        data.decode("utf-8"), object_pairs_hook=unique_object,
        parse_constant=invalid_constant,
    )


def git(checkout, *args):
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(checkout), *args],
    )


def source_files(checkout, profile=ORIGINAL):
    tree = git(checkout, "ls-tree", "-rz", profile.source_commit, "--", f"{profile.template}/Contents")
    blobs = {}
    for entry in tree.rstrip(b"\0").split(b"\0"):
        metadata, source_path = entry.decode("ascii").split("\t", 1)
        mode, kind, object_id = metadata.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"unexpected source type or mode: {source_path}")
        blobs[source_path.removeprefix(profile.template + "/")] = (object_id, mode)
    if set(blobs) != set(profile.files) | set(profile.seeds):
        raise ValueError("the pinned template inventory differs from the controlled lineage")
    return {
        path: (git(checkout, "cat-file", "blob", blobs[path][0]),
               "0555" if blobs[path][1] == "100755" else "0444")
        for path in profile.files
    }


def make_records(files, profile=ORIGINAL):
    sizes = [len(data) for data, _ in files.values()]
    if any(size > MAX_FILE_BYTES for size in sizes) or sum(sizes) > MAX_TOTAL_BYTES:
        raise ValueError("definition exceeds byte limits")
    records = []
    for path in profile.inventory:
        if path in DIRECTORIES:
            records.append({"path": path, "kind": "directory", "mode": "0555"})
        else:
            data, mode = files[path]
            records.append({
                "path": path, "kind": "regular", "mode": mode,
                "size": len(data), "sha256": sha256(data),
            })
    return records


def reviewed_archive_size(records, profile=ORIGINAL):
    if not isinstance(records, list) or len(records) != len(profile.inventory):
        raise ValueError("definition records differ from the controlled inventory")
    total_size = 0
    padded_size = 0
    for path, record in zip(profile.inventory, records):
        if not isinstance(record, dict) or record.get("path") != path:
            raise ValueError("definition records differ from the controlled inventory order")
        if path in DIRECTORIES:
            if record != {"path": path, "kind": "directory", "mode": "0555"}:
                raise ValueError(f"invalid directory record: {path}")
            continue
        size = record.get("size")
        if (set(record) != {"path", "kind", "mode", "size", "sha256"}
                or record["kind"] != "regular" or record["mode"] not in ("0444", "0555")
                or type(size) is not int or not 0 <= size <= MAX_FILE_BYTES
                or not isinstance(record["sha256"], str)
                or not SHA256.fullmatch(record["sha256"])):
            raise ValueError(f"invalid regular record: {path}")
        total_size += size
        padded_size += size + (-size % BLOCK)
    if total_size > MAX_TOTAL_BYTES:
        raise ValueError("definition exceeds the aggregate byte limit")
    return (len(profile.inventory) + 2) * BLOCK + padded_size


def tar_header(record):
    directory = record["kind"] == "directory"
    info = tarfile.TarInfo(record["path"])
    info.type = tarfile.DIRTYPE if directory else tarfile.REGTYPE
    info.mode = int(record["mode"], 8)
    info.size = record.get("size", 0)
    # TarInfo initializes uid, gid and mtime to zero, with empty names.
    return info.tobuf(format=tarfile.USTAR_FORMAT, encoding="ascii", errors="strict")


def write_archive(stream, files, records):
    for record in records:
        stream.write(tar_header(record))
        if record["kind"] == "regular":
            data, _ = files[record["path"]]
            stream.write(data)
            stream.write(bytes(-len(data) % BLOCK))
    stream.write(bytes(2 * BLOCK))


def definition_claim(files):
    info = load_json(files["Contents/SoulInfo.json"][0])
    lock = load_json(files["Contents/SoulLock.json"][0])
    soul_id = info.get("soul_id") if isinstance(info, dict) else None
    claim = lock.get("definition_digest") if isinstance(lock, dict) else None
    if not isinstance(soul_id, str) or not SOUL_ID.fullmatch(soul_id):
        raise ValueError("invalid SoulInfo soul_id")
    if (not isinstance(claim, str) or not claim.startswith("sha256:")
            or not SHA256.fullmatch(claim[7:])):
        raise ValueError("invalid SoulLock definition digest claim")
    return {"soul_id": soul_id, "claimed_definition_digest": claim}


def build(checkout, output, profile=ORIGINAL):
    files = source_files(checkout, profile)
    records = make_records(files, profile)
    reviewed_archive_size(records, profile)
    approved_fields = definition_claim(files)
    with output.open("xb") as stream:
        write_archive(stream, files, records)
    artifact_hash = hashlib.sha256()
    with output.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            artifact_hash.update(chunk)
    result = {
        "artifact_sha256": artifact_hash.hexdigest(),
        **approved_fields,
        "definition_measurement": definition_measurement(records),
        "definition_records": records,
    }
    if profile != ORIGINAL:
        result["candidate_profile"] = profile.name
    return result


def read_archive(stream, records):
    files = {}
    artifact_hash = hashlib.sha256()

    def read(size):
        data = stream.read(size)
        artifact_hash.update(data)
        return data

    for record in records:
        path = record["path"]
        if read(BLOCK) != tar_header(record):
            raise ValueError(f"noncanonical USTAR header: {path}")
        if record["kind"] == "regular":
            size = record["size"]
            data = read(size)
            if len(data) != size or sha256(data) != record["sha256"]:
                raise ValueError(f"changed regular file bytes: {path}")
            if read(-size % BLOCK) != bytes(-size % BLOCK):
                raise ValueError(f"noncanonical USTAR padding: {path}")
            files[path] = (data, record["mode"])
    if read(2 * BLOCK) != bytes(2 * BLOCK) or stream.read(1):
        raise ValueError("invalid USTAR end-of-archive marker")
    return files, artifact_hash.hexdigest()


def verify(artifact, reviewed, profile=ORIGINAL):
    """Compare exact bytes to fields supplied by an already authenticated caller."""
    if not isinstance(reviewed, dict):
        raise ValueError("reviewed fields must be a JSON object")
    if profile != ORIGINAL and reviewed.get("candidate_profile") != profile.name:
        raise ValueError("reviewed fields name a different candidate profile")
    records = reviewed["definition_records"]
    exact_size = reviewed_archive_size(records, profile)
    measured = definition_measurement(records)
    expected_digest = reviewed["artifact_sha256"]
    if not isinstance(expected_digest, str) or not SHA256.fullmatch(expected_digest):
        raise ValueError("invalid reviewed archive digest")
    if measured != reviewed["definition_measurement"]:
        raise ValueError("definition records differ from the reviewed measurement")

    fd = os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        source = os.fstat(stream.fileno())
        if not stat.S_ISREG(source.st_mode) or source.st_nlink != 1 or source.st_size != exact_size:
            raise ValueError("artifact must be one regular file with the reviewed byte size")
        files, artifact_sha256 = read_archive(stream, records)
        if artifact_sha256 != expected_digest:
            raise ValueError("archive digest differs from the reviewed digest")
    claim = definition_claim(files)
    if any(reviewed.get(field) != value for field, value in claim.items()):
        raise ValueError("definition claim differs from the reviewed Soul mapping")
    return files


def stage_review_copy(output, files, records, profile=ORIGINAL):
    # Local unprivileged read-back fixture. The caller supplies a trusted,
    # private parent. Machine implements privileged staging independently.
    output.mkdir(mode=0o700)
    for path in DIRECTORIES:
        (output / path).mkdir(mode=0o700)
    for path, (data, mode) in files.items():
        target = output / path
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(int(mode, 8))
    for path in reversed(DIRECTORIES):
        (output / path).chmod(0o555)

    inventory = sorted(p.relative_to(output).as_posix() for p in output.rglob("*"))
    if inventory != list(profile.inventory):
        raise ValueError("staged review copy has unexpected paths")
    observed = make_records({
        path: ((output / path).read_bytes(), f"{stat.S_IMODE((output / path).stat().st_mode):04o}")
        for path in profile.files
    }, profile)
    if (observed != records
            or any(stat.S_IMODE((output / path).stat().st_mode) != 0o555 for path in DIRECTORIES)):
        raise ValueError("staged review copy differs from reviewed records")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("build")
    create.add_argument("conformance_checkout", type=Path)
    create.add_argument("output_artifact", type=Path)
    create.add_argument("--profile", choices=PROFILES, default=ORIGINAL.name)
    check = commands.add_parser("verify")
    check.add_argument("artifact", type=Path)
    check.add_argument("reviewed_fields", type=Path)
    check.add_argument("--stage-review-copy", type=Path)
    check.add_argument("--profile", choices=PROFILES, default=ORIGINAL.name)
    args = parser.parse_args()
    try:
        profile = PROFILES[args.profile]
        if args.command == "build":
            result = build(args.conformance_checkout, args.output_artifact, profile)
        else:
            result = load_json(args.reviewed_fields.read_bytes())
            files = verify(args.artifact, result, profile)
            if args.stage_review_copy:
                stage_review_copy(args.stage_review_copy, files, result["definition_records"], profile)
        print(json.dumps(result, sort_keys=True, indent=2))
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"{err}\n")


if __name__ == "__main__":
    main()
