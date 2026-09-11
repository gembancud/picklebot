import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_actor import source_record_text, player_source_hash, contact_source_hash


class SourceIdentityTests(unittest.TestCase):
    def test_windows_paths_newlines_and_enumeration_match_posix(self):
        posix = [("Assets/A.cs", "a\nb\n"), ("Assets/nested/B.cs", "c\n")]
        windows = [("Assets\\nested\\B.cs", "c\r"), ("Assets\\A.cs", "a\r\nb\r\n")]
        self.assertEqual(source_record_text(posix), source_record_text(windows))

    def test_ordinal_order_preserves_case(self):
        self.assertEqual(source_record_text([("a.cs", "a"), ("Z.cs", "z")]), "Z.cs\nz\na.cs\na")

    def test_real_source_edits_change_identity_but_tests_do_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            code = root / "Assets/Picklebot/Core/A.cs"
            test = root / "Assets/Picklebot/PlayerAgents/Tests/Editor/T.cs"
            code.parent.mkdir(parents=True)
            test.parent.mkdir(parents=True)
            code.write_bytes(b"class A {}\r\n")
            before = player_source_hash(root)
            test.write_text("ignored test")
            self.assertEqual(before, player_source_hash(root))
            code.write_bytes(b"\xef\xbb\xbfclass A {}\n")
            self.assertEqual(before, player_source_hash(root))
            code.write_text("class A { int changed; }\n")
            self.assertNotEqual(before, player_source_hash(root))

    def test_contact_excludes_only_named_presenters_and_test_folders(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = root / "Assets/Picklebot/Doubles"
            (base / "Tests").mkdir(parents=True)
            before = contact_source_hash(root)
            (base / "DoublesDemo.cs").write_text("presentation")
            (base / "Tests/T.cs").write_text("test")
            self.assertEqual(before, contact_source_hash(root))
            (base / "Contest.cs").write_text("runtime")
            self.assertNotEqual(before, contact_source_hash(root))
