#!/usr/bin/env python3
"""Prepare an unsigned frozen Soul Statement or check an external bundle's shape."""

import argparse
import base64
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tarfile

import stage2a_hello_package as package


REPOSITORY = "true-line/soul-package"
WORKFLOW = ".github/workflows/stage2a-frozen-soul-receipt.yml"
SOURCE_REPO = "true-line/soul-conformance"
SOURCE_TREE = "5f3ab3acee16de02a38a51204fb9401c3566a6d0"
TEMPLATE_TREE = "e944d40e5f495f6de395619b254ed890e36b53ee"
PREDICATE_TYPE = "https://true-line.ai/soul-contracts/package/v1/frozen-soul-build"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
BUNDLE_TYPE = "application/vnd.dev.sigstore.bundle.v0.3+json"
DSSE_TYPE = "application/vnd.in-toto+json"
LOG_VERSIONS = {"dsse": "0.0.1", "hashedrekord": "0.0.2"}
BUILDER_ROOT = Path(__file__).resolve().parents[1]
BUILD_SOURCES = (
    WORKFLOW, "tools/stage2a_hello_package.py", "tools/stage2a_hello_receipt.py",
)
MAX_BUNDLE_BYTES = 1 << 20
MAX_STATEMENT_BYTES = 16 << 10


def require(condition, message):
    if not condition:
        raise ValueError(message)


def matches(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def object_fields(value, fields, label):
    require(isinstance(value, dict) and set(value) == set(fields), f"wrong {label} fields")
    return value


def digested_map(value):
    return "sha256:" + package.sha256(package.canonical_records(value))


def read_bounded(path, maximum):
    with path.open("rb") as stream:
        value = stream.read(maximum + 1)
    require(0 < len(value) <= maximum, f"invalid {path.name} byte length")
    return value


def git_value(checkout, *args):
    return package.git(checkout, *args).decode("ascii").strip()


def actions_source(checkout, env):
    require(env["GITHUB_REPOSITORY"] == REPOSITORY, "wrong builder repository")
    require(env["GITHUB_REF"] == "refs/heads/main" and env["GITHUB_REF_PROTECTED"] == "true",
            "candidate build requires protected main")
    require(env["GITHUB_WORKFLOW_REF"] == f"{REPOSITORY}/{WORKFLOW}@refs/heads/main",
            "wrong workflow identity")
    commit = git_value(checkout, "rev-parse", "HEAD")
    require(env["GITHUB_SHA"] == commit and env["GITHUB_WORKFLOW_SHA"] == commit,
            "checkout, workflow and Actions source commit differ")
    source_hashes = {}
    for path in BUILD_SOURCES:
        raw = (checkout / path).read_bytes()
        require(raw == package.git(checkout, "show", f"{commit}:{path}"),
                f"builder input differs from committed bytes: {path}")
        source_hashes[path] = package.sha256(raw)
    run_attempt = env["GITHUB_RUN_ATTEMPT"]
    require(matches(run_attempt, r"[1-9][0-9]{0,8}"), "invalid Actions run attempt")
    return {
        "repository": REPOSITORY,
        "source_commit": commit,
        "source_tree": git_value(checkout, "rev-parse", "HEAD^{tree}"),
        "workflow": WORKFLOW,
        "run_id": env["GITHUB_RUN_ID"],
        "run_attempt": int(run_attempt),
        "builder_sha256": digested_map(source_hashes),
    }


def toolchain_facts():
    git_path = shutil.which("git")
    require(git_path is not None, "missing Git executable")
    return {
        "git_version": git_value(BUILDER_ROOT, "--version"),
        "git_binary_sha256": package.sha256(Path(git_path).read_bytes()),
        "python_version": sys.version,
        "python_binary_sha256": package.sha256(Path(sys.executable).read_bytes()),
        "tarfile_sha256": package.sha256(Path(tarfile.__file__).read_bytes()),
    }


def statement_bytes(reviewed, builder, toolchain_sha256):
    object_fields(builder, (
        "repository", "source_commit", "source_tree", "workflow", "run_id",
        "run_attempt", "builder_sha256",
    ), "builder")
    require(builder["repository"] == REPOSITORY and builder["workflow"] == WORKFLOW,
            "unexpected builder identity")
    require(all(matches(builder[field], r"[0-9a-f]{40}") for field in ("source_commit", "source_tree")),
            "invalid builder commit or tree")
    require(matches(builder["run_id"], r"[1-9][0-9]{0,19}")
            and type(builder["run_attempt"]) is int and 1 <= builder["run_attempt"] <= 999_999_999,
            "invalid Actions run identity")
    for value in (builder["builder_sha256"], toolchain_sha256, reviewed["definition_measurement"]):
        require(matches(value, r"sha256:[0-9a-f]{64}"), "invalid prefixed digest")
    digest = reviewed["artifact_sha256"]
    require(matches(digest, r"[0-9a-f]{64}"), "invalid frozen artifact digest")
    return package.canonical_records({
        "_type": STATEMENT_TYPE,
        "predicateType": PREDICATE_TYPE,
        "subject": [{"name": f"sha256-{digest}.soul", "digest": {"sha256": digest}}],
        "predicate": {
            "artifact_format": "stage2a-frozen-hello-ustar/v1",
            "builder": builder,
            "toolchain_sha256": toolchain_sha256,
            "template": {
                "repository": SOURCE_REPO,
                "source_commit": package.SOURCE_COMMIT,
                "source_tree": SOURCE_TREE,
                "path": package.TEMPLATE,
                "template_tree": TEMPLATE_TREE,
            },
            "definition_measurement": reviewed["definition_measurement"],
        },
    })


def prepare(template, output, env):
    builder = actions_source(BUILDER_ROOT, env)
    require(git_value(template, "rev-parse", f"{package.SOURCE_COMMIT}^{{tree}}") == SOURCE_TREE
            and git_value(template, "rev-parse", f"{package.SOURCE_COMMIT}:{package.TEMPLATE}") == TEMPLATE_TREE,
            "pinned template tree differs")
    toolchain = toolchain_facts()
    output.mkdir(mode=0o700)
    temporary_archive = output / "build.soul"
    reviewed = package.build(template, temporary_archive)
    artifact = output / f"sha256-{reviewed['artifact_sha256']}.soul"
    temporary_archive.rename(artifact)
    package.verify(artifact, reviewed)
    (output / "review-fields.json").write_bytes(package.canonical_records(reviewed))
    (output / "toolchain.json").write_bytes(package.canonical_records(toolchain))
    (output / "statement.json").write_bytes(statement_bytes(reviewed, builder, digested_map(toolchain)))


def decode_bytes(value, label):
    require(isinstance(value, str) and value, f"missing {label}")
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError as err:
        raise ValueError(f"invalid {label} base64") from err
    require(decoded and base64.b64encode(decoded).decode("ascii") == value, f"noncanonical {label} base64")
    return decoded


def bundle_shape(raw, expected, log_kind, log_version):
    require(LOG_VERSIONS.get(log_kind) == log_version, "unsupported candidate Rekor entry type")
    bundle = object_fields(package.load_json(raw), ("mediaType", "verificationMaterial", "dsseEnvelope"), "bundle")
    require(bundle["mediaType"] == BUNDLE_TYPE, "wrong bundle media type")
    envelope = object_fields(bundle["dsseEnvelope"], ("payloadType", "payload", "signatures"), "DSSE envelope")
    require(envelope["payloadType"] == DSSE_TYPE, "wrong DSSE payload type")
    require(decode_bytes(envelope["payload"], "DSSE payload") == expected, "DSSE payload differs from exact expected Statement")
    signatures = envelope["signatures"]
    require(isinstance(signatures, list) and len(signatures) == 1 and isinstance(signatures[0], dict),
            "expected one DSSE signature")
    decode_bytes(signatures[0].get("sig"), "DSSE signature")
    material = bundle["verificationMaterial"]
    require(isinstance(material, dict) and set(material) in (
        {"certificate", "tlogEntries"}, {"certificate", "tlogEntries", "timestampVerificationData"},
    ), "wrong verification material fields")
    certificate = object_fields(material["certificate"], ("rawBytes",), "leaf certificate")
    decode_bytes(certificate["rawBytes"], "leaf certificate")
    entries = material["tlogEntries"]
    require(isinstance(entries, list) and len(entries) == 1 and isinstance(entries[0], dict),
            "expected one transparency log entry")
    entry = entries[0]
    require(entry.get("kindVersion") == {"kind": log_kind, "version": log_version}, "unexpected Rekor entry type")
    proof = entry.get("inclusionProof")
    require(isinstance(proof, dict) and isinstance(proof.get("checkpoint"), dict)
            and isinstance(proof["checkpoint"].get("envelope"), str) and proof["checkpoint"]["envelope"],
            "missing inclusion proof checkpoint")
    promise = entry.get("inclusionPromise", {})
    timestamps = material.get("timestampVerificationData", {})
    require(isinstance(promise, dict) and isinstance(timestamps, dict), "malformed signing-time material")
    rfc3161 = timestamps.get("rfc3161Timestamps", [])
    require(isinstance(rfc3161, list), "malformed RFC 3161 timestamps")
    if log_kind == "dsse" and "signedEntryTimestamp" in promise:
        decode_bytes(promise["signedEntryTimestamp"], "signed entry timestamp")
    else:
        require(len(rfc3161) == 1 and isinstance(rfc3161[0], dict), "missing candidate signing-time proof")
        decode_bytes(rfc3161[0].get("signedTimestamp"), "RFC 3161 timestamp")


def check_bundle(artifact, review_path, expected_path, bundle_path, log_kind, log_version):
    reviewed = package.load_json(read_bounded(review_path, MAX_STATEMENT_BYTES))
    package.verify(artifact, reviewed)
    expected = read_bounded(expected_path, MAX_STATEMENT_BYTES)
    statement = object_fields(package.load_json(expected), ("_type", "predicateType", "subject", "predicate"), "Statement")
    predicate = object_fields(statement["predicate"], (
        "artifact_format", "builder", "toolchain_sha256", "template", "definition_measurement",
    ), "predicate")
    require(expected == statement_bytes(reviewed, predicate["builder"], predicate["toolchain_sha256"]),
            "candidate Statement differs from the exact frozen artifact and predicate")
    bundle = read_bounded(bundle_path, MAX_BUNDLE_BYTES)
    bundle_shape(bundle, expected, log_kind, log_version)
    return {
        "artifact_sha256": reviewed["artifact_sha256"],
        "bundle_sha256": package.sha256(bundle),
        "statement_sha256": package.sha256(expected),
        "status": "shape-checked-only",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("template_checkout", type=Path)
    build.add_argument("output_directory", type=Path)
    check = commands.add_parser("check-bundle")
    for name in ("artifact", "review_fields", "expected_statement", "bundle"):
        check.add_argument(name, type=Path)
    check.add_argument("--log-kind", required=True)
    check.add_argument("--log-version", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.template_checkout, args.output_directory, os.environ)
        else:
            result = check_bundle(args.artifact, args.review_fields, args.expected_statement,
                                  args.bundle, args.log_kind, args.log_version)
            print(package.canonical_records(result).decode("ascii"))
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"{err}\n")


if __name__ == "__main__":
    main()
