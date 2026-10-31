#!/usr/bin/env python3
"""Independent brute-force tests for mrc_data_statistics.py (stdlib only)."""

import contextlib
import csv
from fractions import Fraction
from io import StringIO
from itertools import combinations
from math import comb
from pathlib import Path
import tempfile
import unittest

import mrc_data_statistics as mrc


def enumerate_grid(r, c):
    """Independent enumeration (not transfer matrix): inspect every occupancy subset."""
    n = r*c
    edges = []
    for y in range(r):
        for x in range(c):
            j = y*c + x
            if x+1 < c:
                edges.append((j, j+1))
            if y+1 < r:
                edges.append((j, j+c))
    result = {}
    for o in range(n+1):
        frequencies = {}
        for chosen in combinations(range(n), o):
            selected = set(chosen)
            a = sum(u in selected and v in selected for u, v in edges)
            frequencies[a] = frequencies.get(a, 0) + 1
        result[o] = frequencies
    return result


def make_csv(directory, r, c, data, dense=True, sentinel=True):
    path = directory / f"{r}.{c}.csv"
    edges = 2*r*c-r-c
    with path.open('w', newline='', encoding='utf-8') as out:
        wr = csv.writer(out)
        wr.writerow(('r','c','o','a','count'))
        for o in sorted(data):
            for a in range(edges+1) if dense else sorted(data[o]):
                wr.writerow([r,c,o,a,data[o].get(a,0)])
        if sentinel:
            out.write('.DONE.\n')
    return path


class TestMRCDataStatistics(unittest.TestCase):
    def test_all_small_grids_and_occupancies(self):
        for r,c in [(1,1), (1,4), (2,2), (2,3), (3,3)]:
            with self.subTest(shape=(r,c)), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                data = enumerate_grid(r,c)
                src = make_csv(directory, r,c, data)
                for o in range(r*c+1):
                    table = mrc.read_occupancy(src,r,c,o)
                    for a in range(2*r*c-r-c+1):
                        stats = mrc.calculate_statistics(r,c,o,a,table)
                        self.assertEqual(int(stats['count']), data[o].get(a,0))
                        self.assertEqual(int(stats['total_placements']), comb(r*c,o))
                        self.assertEqual(stats['attainable'], data[o].get(a,0)>0)
                        self.assertEqual(stats['probabilities']['pmf']['exact'],
                                         mrc.rational_json(Fraction(data[o].get(a,0),comb(r*c,o))))
                        if stats['attainable'] and stats['amin'] != stats['amax']:
                            bounded = Fraction(stats['bounded_aggregation'])
                            self.assertGreaterEqual(bounded,0)
                            self.assertLessEqual(bounded,1)
                        if stats['attainable'] and stats['variance_exact']['numerator'] != '0':
                            centered = Fraction(stats['bounded_centered_deviation'])
                            self.assertGreaterEqual(centered,-1)
                            self.assertLessEqual(centered,1)

    def test_known_2x2(self):
        data = enumerate_grid(2,2)
        stats = mrc.calculate_statistics(2,2,2,0,data[2])
        self.assertEqual(stats['count'],'2')
        self.assertEqual(stats['mean_exact'],mrc.rational_json(Fraction(2,3)))
        self.assertEqual(stats['variance_exact'],mrc.rational_json(Fraction(2,9)))
        self.assertEqual(stats['probabilities']['tail_lt']['exact'],
                         mrc.rational_json(Fraction(0)))
        self.assertEqual(stats['probabilities']['tail_ge']['exact'],
                         mrc.rational_json(Fraction(1)))
        self.assertEqual(stats['probabilities']['two_sided_distance_p']['exact'],
                         mrc.rational_json(Fraction(1,3)))
        self.assertEqual(stats['bounded_centered_deviation'],'-1')

    def test_orientation_sparse_and_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            data = enumerate_grid(2,3)
            make_csv(directory,2,3,data,dense=False)
            path = mrc.locate_csv(directory,3,2)
            self.assertEqual(path.name,'2.3.csv')
            table = mrc.read_occupancy(path,3,2,3)
            mrc.calculate_statistics(3,2,3,2,table)
            out=directory/'distribution.csv'
            mrc.write_distribution(out,3,2,3,table,12)
            with out.open() as handle:
                records=list(csv.DictReader(handle))
            self.assertEqual(len(records), 2*6-3-2+1)
            self.assertEqual(sum(int(x['count']) for x in records), comb(6,3))

    def test_incomplete_and_corrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            data = enumerate_grid(2,3)
            src = make_csv(folder,2,3,data,sentinel=False)
            with self.assertRaisesRegex(mrc.MRCDataError,'sentinel'):
                mrc.read_occupancy(src,2,3,2)
            src = make_csv(folder,2,3,data)
            with src.open('a') as out:
                out.write('2,3,2,1,10\n')
            with self.assertRaisesRegex(mrc.MRCDataError,'after'):
                mrc.read_occupancy(src,2,3,2)
            src = make_csv(folder,2,3,data)
            contents=src.read_text()
            src.write_text(contents.replace('2,3,2,0,', '2,3,2,1,', 1))
            with self.assertRaisesRegex(mrc.MRCDataError, 'Duplicate'):
                mrc.read_occupancy(src,2,3,2)
            src = make_csv(folder,2,3,data)
            contents=src.read_text()
            src.write_text(contents.replace('2,3,2,1,', '2,3,2,1,999', 1))
            with self.assertRaises(mrc.MRCDataError):
                mrc.read_occupancy(src,2,3,2)

    def test_moment_integrity_catches_wrong_distribution(self):
        data=enumerate_grid(3,3)
        table = dict(data[4])
        # Transfer one configuration from one attainable a to another while
        # preserving the normalization, which a sum-only check would miss.
        keys=sorted(k for k,v in table.items() if v>1)
        self.assertGreaterEqual(len(keys),2)
        table[keys[0]]-=1
        table[keys[1]]+=1
        self.assertEqual(sum(table.values()),comb(9,4))
        with self.assertRaisesRegex(mrc.MRCDataError, 'moment'):
            mrc.calculate_statistics(3,3,4,keys[0],table)

    def test_cli_json_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            make_csv(folder,2,2,enumerate_grid(2,2))
            with contextlib.redirect_stdout(StringIO()) as out:
                code=mrc.main(['2','2','2','1','--data-dir',str(folder),'--json'])
            self.assertEqual(code,0)
            self.assertIn('"pmf"',out.getvalue())
            with contextlib.redirect_stdout(StringIO()) as out:
                code=mrc.main(['2','2','2','1','--data-dir',str(folder)])
            self.assertEqual(code,0)
            self.assertIn('AGGREGATION SCORES',out.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
