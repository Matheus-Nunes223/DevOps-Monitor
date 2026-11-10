import tempfile
import unittest
from pathlib import Path

from monitor.logtail import LogTail


class LogTailTests(unittest.TestCase):
    def test_starts_at_end_and_reads_only_new_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            path.write_text("old line\n", encoding="utf-8")
            tail = LogTail(path)
            with path.open("a", encoding="utf-8") as stream:
                stream.write("new line\n")
            self.assertEqual(tail.read_new_lines(), ["new line"])
            self.assertEqual(tail.read_new_lines(), [])

    def test_retains_partial_line_until_newline_arrives(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            path.write_text("", encoding="utf-8")
            tail = LogTail(path, start_at_end=False)
            with path.open("a", encoding="utf-8") as stream:
                stream.write("partial")
            self.assertEqual(tail.read_new_lines(), [])
            with path.open("a", encoding="utf-8") as stream:
                stream.write(" line\nnext\n")
            self.assertEqual(tail.read_new_lines(), ["partial line", "next"])

    def test_detects_truncation_of_same_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            path.write_text("first line\nsecond line\n", encoding="utf-8")
            tail = LogTail(path, start_at_end=False)
            self.assertEqual(tail.read_new_lines(), ["first line", "second line"])
            path.write_text("after truncate\n", encoding="utf-8")
            self.assertEqual(tail.read_new_lines(), ["after truncate"])

    def test_detects_file_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "access.log"
            rotated = Path(directory) / "access.log.1"
            path.write_text("before rotation\n", encoding="utf-8")
            tail = LogTail(path, start_at_end=False)
            self.assertEqual(tail.read_new_lines(), ["before rotation"])
            path.rename(rotated)
            path.write_text("after rotation\n", encoding="utf-8")
            self.assertEqual(tail.read_new_lines(), ["after rotation"])

    def test_missing_file_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            tail = LogTail(Path(directory) / "missing.log")
            with self.assertRaises(FileNotFoundError):
                tail.read_new_lines()


if __name__ == "__main__":
    unittest.main()
