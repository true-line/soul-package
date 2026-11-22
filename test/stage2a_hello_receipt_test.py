import base64
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stage2a_hello_package as package
import stage2a_hello_receipt as receipt


def encoded(value):
    return base64.b64encode(value).decode("ascii")


class HelloReceiptTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / "hello.soul"
        self.fields = self.root / "review-fields.json"
        self.statement = self.root / "statement.json"
        self.bundle = self.root / "bundle.json"
        files = {p: (b"fixture", "0444") for p in package.FILES}
        files["Contents/SoulInfo.json"] = (
            b'{"soul_id":"agent_00000000-0000-0000-0000-000000000000"}', "0444",
        )
        files["Contents/SoulLock.json"] = (
            b'{"definition_digest":"sha256:' + b"a" * 64 + b'"}', "0444",
        )
        with patch.object(package, "source_files", return_value=files):
            self.reviewed = package.build(self.root, self.archive)
        self.builder = {
            "repository": receipt.REPOSITORY,
            "source_commit": "1" * 40,
            "source_tree": "2" * 40,
            "workflow": receipt.WORKFLOW,
            "run_id": "12345",
            "run_attempt": 2,
            "builder_sha256": "sha256:" + "3" * 64,
        }
        self.toolchain = "sha256:" + "4" * 64
        expected = receipt.statement_bytes(self.reviewed, self.builder, self.toolchain)
        self.fields.write_bytes(package.canonical_records(self.reviewed))
        self.statement.write_bytes(expected)
        placeholder = encoded(b"synthetic shape only")
        self.fixture = {
            "mediaType": receipt.BUNDLE_TYPE,
            "dsseEnvelope": {
                "payloadType": receipt.DSSE_TYPE,
                "payload": encoded(expected),
                "signatures": [{"sig": placeholder, "keyid": ""}],
            },
            "verificationMaterial": {
                "certificate": {"rawBytes": placeholder},
                "tlogEntries": [{
                    "kindVersion": {"kind": "dsse", "version": "0.0.1"},
                    "inclusionProof": {"checkpoint": {"envelope": "synthetic checkpoint"}},
                    "inclusionPromise": {"signedEntryTimestamp": placeholder},
                }],
            },
        }

    def check(self, bundle=None, kind="dsse", version="0.0.1"):
        self.bundle.write_bytes(package.canonical_records(self.fixture if bundle is None else bundle))
        return receipt.check_bundle(
            self.archive, self.fields, self.statement, self.bundle, kind, version,
        )

    def test_exact_statement_and_sigstore_proto_json_shape(self):
        report = self.check()
        digest = self.reviewed["artifact_sha256"]
        statement = package.load_json(self.statement.read_bytes())
        self.assertEqual(statement["subject"], [{"name": f"sha256-{digest}.soul", "digest": {"sha256": digest}}])
        self.assertEqual(statement["predicateType"], receipt.PREDICATE_TYPE)
        self.assertEqual(statement["predicate"]["definition_measurement"], self.reviewed["definition_measurement"])
        self.assertNotIn("soul_id", statement["predicate"])
        self.assertNotIn("definition_records", statement["predicate"])
        self.assertEqual(report, {
            "artifact_sha256": digest,
            "statement_sha256": package.sha256(self.statement.read_bytes()),
            "bundle_sha256": package.sha256(self.bundle.read_bytes()),
            "status": "shape-checked-only",
        })

    def test_reject_old_envelope_nesting(self):
        self.fixture["content"] = {"dsseEnvelope": self.fixture.pop("dsseEnvelope")}
        with self.assertRaisesRegex(ValueError, "wrong bundle fields"):
            self.check()

    def test_reject_wrong_statement_even_when_expected_and_envelope_agree(self):
        for field in ("predicateType", "subject"):
            original = receipt.statement_bytes(self.reviewed, self.builder, self.toolchain)
            statement = package.load_json(original)
            if field == "predicateType":
                statement[field] = "https://true-line.ai/soul-contracts/adapter/v2/souls-build"
            else:
                statement[field][0]["name"] = "souls-package.tgz"
            changed = package.canonical_records(statement)
            self.statement.write_bytes(changed)
            self.fixture["dsseEnvelope"]["payload"] = encoded(changed)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "exact frozen artifact"):
                self.check()

    def test_reject_replayed_or_noncanonical_payload_and_duplicate_keys(self):
        changed = {**self.builder, "run_attempt": 3}
        payload = receipt.statement_bytes(self.reviewed, changed, self.toolchain)
        for other in (payload, self.statement.read_bytes() + b"\n"):
            self.fixture["dsseEnvelope"]["payload"] = encoded(other)
            with self.assertRaisesRegex(ValueError, "payload differs"):
                self.check()
        self.bundle.write_bytes(b'{"mediaType":"first","mediaType":"second"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            receipt.check_bundle(self.archive, self.fields, self.statement, self.bundle, "dsse", "0.0.1")

    def test_reject_artifact_byte_change(self):
        self.archive.write_bytes(b"different artifact")
        with self.assertRaisesRegex(ValueError, "reviewed byte size"):
            self.check()

    def test_proof_signer_shape_and_log_kind_are_required(self):
        for field, container in (
            ("checkpoint", ("verificationMaterial", "tlogEntries", 0, "inclusionProof")),
            ("inclusionPromise", ("verificationMaterial", "tlogEntries", 0)),
            ("certificate", ("verificationMaterial",)),
            ("signatures", ("dsseEnvelope",)),
        ):
            fixture = deepcopy(self.fixture)
            scope = fixture
            for part in container:
                scope = scope[part]
            del scope[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(fixture)
        with self.assertRaisesRegex(ValueError, "unexpected Rekor entry type"):
            self.check(kind="hashedrekord", version="0.0.2")

    def test_allow_candidate_rfc3161_shape_with_pinned_log_kind(self):
        material = self.fixture["verificationMaterial"]
        entry = material["tlogEntries"][0]
        del entry["inclusionPromise"]
        entry["kindVersion"] = {"kind": "hashedrekord", "version": "0.0.2"}
        with self.assertRaisesRegex(ValueError, "missing candidate signing-time proof"):
            self.check(kind="hashedrekord", version="0.0.2")
        entry["inclusionPromise"] = {"signedEntryTimestamp": encoded(b"not a v2 timestamp")}
        with self.assertRaisesRegex(ValueError, "missing candidate signing-time proof"):
            self.check(kind="hashedrekord", version="0.0.2")
        material["timestampVerificationData"] = {
            "rfc3161Timestamps": [{"signedTimestamp": encoded(b"synthetic timestamp")}],
        }
        self.assertEqual(self.check(kind="hashedrekord", version="0.0.2")["status"], "shape-checked-only")

    def test_wrong_actions_context_stops_before_git(self):
        env = {
            "GITHUB_REPOSITORY": receipt.REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REF_PROTECTED": "false",
        }
        with patch.object(package, "git") as git:
            with self.assertRaisesRegex(ValueError, "protected main"):
                receipt.actions_source(self.root, env)
            git.assert_not_called()


if __name__ == "__main__":
    unittest.main()
