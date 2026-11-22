from copy import deepcopy
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stage2a_hello_package as package


class HelloPackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / "hello.soul"
        self.files = {
            "Contents/SoulInfo.json": (
                b'{"soul_id":"agent_00000000-0000-0000-0000-000000000000"}', "0444",
            ),
            "Contents/SoulLock.json": (
                b'{"definition_digest":"sha256:' + b"c" * 64 + b'"}', "0444",
            ),
            "Contents/opt/quickstart-adapter.mjs": (b"// adapter\n", "0444"),
            "Contents/opt/quickstart-check.mjs": (b"// checker\n", "0444"),
            "Contents/primitives/quickstart-task.json": (b"{}", "0444"),
        }
        with patch.object(package, "source_files", return_value=self.files):
            self.reviewed = package.build(self.root, self.artifact)

    def test_reproducible_archive_and_readback(self):
        repeat = self.root / "repeated.soul"
        different_order = dict(reversed(list(self.files.items())))
        with patch.object(package, "source_files", return_value=different_order):
            self.assertEqual(package.build(self.root, repeat), self.reviewed)
        self.assertEqual(repeat.read_bytes(), self.artifact.read_bytes())
        with tarfile.open(self.artifact, "r:") as archive:
            self.assertEqual(archive.getnames(), list(package.INVENTORY))
            for name, (data, _) in self.files.items():
                self.assertEqual(archive.extractfile(name).read(), data)

        copy = self.root / "readback.soul"
        extracted = package.verify(self.artifact, self.reviewed)
        package.stage_review_copy(copy, extracted, self.reviewed["definition_records"])
        for directory in package.DIRECTORIES:
            self.addCleanup((copy / directory).chmod, 0o700)
        self.assertFalse((copy / "Contents/workspaces").exists())
        self.assertFalse((copy / "Contents/host").exists())
        with self.assertRaises(FileExistsError):
            package.stage_review_copy(copy, extracted, self.reviewed["definition_records"])

    def test_pinned_source_candidate_fixture_and_tampering(self):
        fixture = Path(__file__).resolve().parent / "fixtures/stage2a-hello"
        archive = fixture / "hello.soul"
        reviewed = package.load_json((fixture / "review-fields.json").read_bytes())
        self.assertEqual(archive.stat().st_size, 10_240)
        self.assertEqual(reviewed["artifact_sha256"],
                         "91492287cced24a5f893fdad4516f23f4f4162df8f449a979f35ea8b70adfe47")
        self.assertEqual(reviewed["soul_id"], "agent_0b3f1e2a-7c4d-4e8f-9a1b-2c3d4e5f6a7b")
        self.assertEqual(reviewed["definition_measurement"],
                         "sha256:68651e0685e0267f343e8b500d4af764a882c4ee56f0d1b4d2c775538317a621")
        self.assertEqual(set(package.verify(archive, reviewed)), set(package.FILES))
        changed = self.root / "altered-candidate.soul"
        raw = bytearray(archive.read_bytes())
        raw[2 * package.BLOCK] ^= 1
        changed.write_bytes(raw)
        with self.assertRaises(ValueError):
            package.verify(changed, reviewed)
        with self.assertRaises(ValueError):
            package.verify(archive, {**reviewed, "soul_id": "agent_ffffffff-ffff-ffff-ffff-ffffffffffff"})

    def test_exact_receipt_and_owner_mapping(self):
        mutations = {
            "artifact_sha256": "0" * 64,
            "soul_id": "agent_10000000-0000-0000-0000-000000000000",
            "claimed_definition_digest": "sha256:" + "a" * 64,
            "definition_measurement": "sha256:" + "b" * 64,
        }
        for field, value in mutations.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                package.verify(self.artifact, {**self.reviewed, field: value})

    def test_exact_inventory_and_limits_before_read(self):
        records = self.reviewed["definition_records"]
        for item in (
            records[1:],
            records[::-1],
            [*records, records[-1]],
            [*records[:-1], {**records[-1], "path": "Contents/opt/../secret"}],
            [*records[:-1], {**records[-1], "path": "Contents/Primitives/quickstart-task.json"}],
            [*records[:-1], {**records[-1], "size": package.MAX_FILE_BYTES + 1}],
            [*records[:-1], {**records[-1], "mode": "0644"}],
        ):
            with self.subTest(item=item), self.assertRaises(ValueError):
                package.verify(self.root / "missing", {**self.reviewed, "definition_records": item})

    def test_byte_tampering_refuses_even_with_matching_archive_digest(self):
        pristine = self.artifact.read_bytes()
        contents_offset = 2 * package.BLOCK
        padding_offset = contents_offset + len(self.files["Contents/SoulInfo.json"][0])
        for offset in (0, contents_offset, padding_offset, len(pristine) - 1):
            tampered = bytearray(pristine)
            tampered[offset] ^= 1
            self.artifact.write_bytes(tampered)
            digest = package.sha256(tampered)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                package.verify(self.artifact, {**self.reviewed, "artifact_sha256": digest})
        for data in (pristine[:-1], pristine + b"\0"):
            self.artifact.write_bytes(data)
            with self.assertRaises(ValueError):
                package.verify(self.artifact, self.reviewed)

    def test_valid_tar_alternatives_refuse(self):
        pristine = self.artifact.read_bytes()
        for name, kind, mtime in (
            ("../outside", tarfile.REGTYPE, 0),
            ("Contents/SoulLock.json", tarfile.REGTYPE, 0),
            ("Contents/workspaces/scratch/extra.txt", tarfile.REGTYPE, 0),
            ("Contents/SoulInfo.json", tarfile.SYMTYPE, 0),
            ("Contents/SoulInfo.json", tarfile.LNKTYPE, 0),
            ("Contents/SoulInfo.json", tarfile.REGTYPE, 1),
        ):
            info = tarfile.TarInfo(name)
            info.type, info.mtime, info.mode = kind, mtime, 0o444
            info.size = len(self.files["Contents/SoulInfo.json"][0])
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                info.linkname = "Contents/SoulLock.json"
            header = info.tobuf(format=tarfile.USTAR_FORMAT)
            tampered = pristine[:package.BLOCK] + header + pristine[2 * package.BLOCK:]
            self.artifact.write_bytes(tampered)
            with self.subTest(name=name, kind=kind, mtime=mtime), self.assertRaisesRegex(
                ValueError, "noncanonical USTAR header"
            ):
                package.verify(self.artifact, {**self.reviewed, "artifact_sha256": package.sha256(tampered)})

        appended = pristine[:-2 * package.BLOCK] + pristine[:package.BLOCK] + pristine[-2 * package.BLOCK:]
        self.artifact.write_bytes(appended)
        with self.assertRaisesRegex(ValueError, "reviewed byte size"):
            package.verify(self.artifact, {**self.reviewed, "artifact_sha256": package.sha256(appended)})

    def test_consistent_self_claim_requires_reviewed_measurement(self):
        other_files = deepcopy(self.files)
        other_files["Contents/opt/quickstart-check.mjs"] = (b"// different checker\n", "0444")
        other = self.root / "other.soul"
        with patch.object(package, "source_files", return_value=other_files):
            other_summary = package.build(self.root, other)
        self.assertEqual(other_summary["claimed_definition_digest"], self.reviewed["claimed_definition_digest"])
        self.assertNotEqual(other_summary["definition_measurement"], self.reviewed["definition_measurement"])
        with self.assertRaises(ValueError):
            package.verify(other, self.reviewed)

    def test_links_refuse(self):
        symlink = self.root / "symlink.soul"
        symlink.symlink_to(self.artifact)
        with self.assertRaises(OSError):
            package.verify(symlink, self.reviewed)
        os.link(self.artifact, self.root / "hardlink.soul")
        with self.assertRaisesRegex(ValueError, "one regular file"):
            package.verify(self.artifact, self.reviewed)

    def test_output_path_must_be_new(self):
        original = self.artifact.read_bytes()
        with patch.object(package, "source_files", return_value=self.files):
            with self.assertRaises(FileExistsError):
                package.build(self.root, self.artifact)
        self.assertEqual(self.artifact.read_bytes(), original)

    def test_duplicate_metadata_keys_refuse(self):
        files = deepcopy(self.files)
        files["Contents/SoulLock.json"] = (
            b'{"definition_digest":"sha256:' + b"c" * 64 + b'","definition_digest":"duplicate"}',
            "0444",
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            package.definition_claim(files)


if __name__ == "__main__":
    unittest.main()
