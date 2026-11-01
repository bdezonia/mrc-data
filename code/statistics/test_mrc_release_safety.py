#!/usr/bin/env python3
"""Release hardening regression tests: archive inputs must never be overwritten."""
import contextlib
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import mrc_data_statistics as mrc


class TestArchiveOutputProtection(unittest.TestCase):
    def test_all_export_modes_reject_archive_filename(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_dir = root / 'data'
            data_dir.mkdir()
            # The table must remain unchanged, regardless of requested output.
            src = data_dir / '1.1.csv'
            contents = 'r,c,o,a,count\n1,1,0,0,1\n1,1,1,0,1\n.DONE.\n'
            src.write_text(contents)
            inp = root / 'observations.csv'
            inp.write_text('r,c,o,a\n1,1,1,0\n')
            for arguments in (
                ['1','1','1','0','--export-csv',str(src)],
                ['1','1','1','--thermo','--output',str(src)],
                ['--batch',str(inp),'--output',str(src)],
            ):
                with self.subTest(arguments=arguments), contextlib.redirect_stderr(StringIO()), contextlib.redirect_stdout(StringIO()):
                    code = mrc.main(arguments + ['--data-dir',str(data_dir)])
                self.assertEqual(code,2)
                self.assertEqual(src.read_text(),contents)

    def test_export_to_different_table_name_also_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); data_dir=root/'data'; data_dir.mkdir()
            src=data_dir/'1.1.csv'
            src.write_text('r,c,o,a,count\n1,1,0,0,1\n1,1,1,0,1\n.DONE.\n')
            other=data_dir/'2.2.csv'
            with contextlib.redirect_stderr(StringIO()),contextlib.redirect_stdout(StringIO()):
                code=mrc.main(['1','1','0','0','--export-csv',str(other),'--data-dir',str(data_dir)])
            self.assertEqual(code,2)
            self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
