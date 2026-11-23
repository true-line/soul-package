from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import stage2a_hello_package as package


class StockHelloPackageTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {
            "Contents/SoulInfo.json": (b'{"soul_id":"agent_0b3f1e2a-7c4d-4e8f-9a1b-2c3d4e5f6a7b"}', "0444"),
            "Contents/SoulLock.json": (b'{"definition_digest":"sha256:' + b"d" * 64 + b'"}', "0444"),
            "Contents/opt/stock-claude.json": (b'{"adapter_id":"claude-code"}', "0444"),
            "Contents/primitives/qualification-task.json": (b'{"objective":"Return the fixture response."}', "0444"),
        }

    def test_pinned_profile_is_distinct_from_the_original(self):
        self.assertEqual(package.STOCK.source_commit, "068f5dd4d6f17691e66ea6cb3d126a0e40971f9a")
        self.assertEqual(package.STOCK.template, "templates/stage2a-stock-hello.soul")
        self.assertEqual(set(package.STOCK.files), set(self.files))
        self.assertNotEqual(package.STOCK.inventory, package.ORIGINAL.inventory)

    def test_stock_archive_repeats_and_refuses_other_profile_or_altered_bytes(self):
        first, second = self.root / "first.soul", self.root / "second.soul"
        with patch.object(package, "source_files", return_value=self.files):
            reviewed = package.build(self.root, first, package.STOCK)
            repeated = package.build(self.root, second, package.STOCK)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(reviewed, repeated)
        self.assertEqual(reviewed["candidate_profile"], package.STOCK.name)
        self.assertEqual(set(package.verify(first, reviewed, package.STOCK)), set(self.files))
        with self.assertRaises(ValueError):
            package.verify(first, reviewed)
        with self.assertRaises(ValueError):
            package.verify(first, {**reviewed, "candidate_profile": "other"}, package.STOCK)
        with self.assertRaises(ValueError):
            package.verify(first, {**reviewed,
                                   "soul_id": "agent_ffffffff-ffff-ffff-ffff-ffffffffffff"}, package.STOCK)
        altered = self.root / "altered.soul"
        raw = bytearray(first.read_bytes())
        raw[2 * package.BLOCK] ^= 1
        altered.write_bytes(raw)
        with self.assertRaises(ValueError):
            package.verify(altered, reviewed, package.STOCK)

        staged = self.root / "staged"
        package.stage_review_copy(staged, package.verify(first, reviewed, package.STOCK),
                                  reviewed["definition_records"], package.STOCK)
        self.assertEqual(sorted(path.relative_to(staged).as_posix() for path in staged.rglob("*")),
                         list(package.STOCK.inventory))
        for directory in reversed(package.DIRECTORIES):
            (staged / directory).chmod(0o700)


if __name__ == "__main__":
    unittest.main()
