#!/usr/bin/env python3
"""Regression checks for mrc_archive_validate.py. Run: python3 -m unittest -v"""
import csv
from pathlib import Path
import tempfile
import unittest

from mrc_archive_validate import (
    AuditError, PROBES, audit_file, brute_counts, expected_edge_case_rows,
    expected_moments, edges_and_degrees, naive_transfer_evaluation,
    pair_triple_edge_counts,
)


def write_grid(path, r, c, changes=None, sentinel=True):
    counts = brute_counts(r, c)
    e = len(edges_and_degrees(r, c)[0])
    if changes:
        for (o, a), change in changes.items():
            counts[(o, a)] = counts.get((o, a), 0) + change
            if counts[(o, a)] < 0:
                raise ValueError("test introduced a negative count")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["r", "c", "o", "a", "count"])
        for o in range(r*c+1):
            for a in range(e+1):
                writer.writerow([r,c,o,a,counts.get((o,a),0)])
        if sentinel:
            f.write(".DONE.\n")


class TestMRCArchiveValidator(unittest.TestCase):
    def test_independent_graph_moments_agree_with_enumeration(self):
        for r, c in [(1,1),(1,2),(1,5),(2,2),(2,3),(2,4),(3,3),(3,4),(4,4)]:
            with self.subTest(r=r, c=c):
                counts = brute_counts(r, c)
                info = pair_triple_edge_counts(r, c)
                for o in range(r*c+1):
                    actual = tuple(sum(
                        (1, a, a*(a-1)//2, a*(a-1)*(a-2)//6)[k] * value
                        for (oo,a),value in counts.items() if oo==o)
                        for k in range(4))
                    self.assertEqual(actual,expected_moments(r,c,o,info))
                for o, row in expected_edge_case_rows(r,c,info).items():
                    actual = {a:value for (oo,a),value in counts.items() if oo==o}
                    self.assertEqual(actual, {a:value for a,value in row.items() if value})

    def test_valid_dense_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            for r, c in [(1,1),(1,5),(2,3),(3,3),(3,4),(4,4)]:
                path = Path(temp)/f"{r}.{c}.csv"
                write_grid(path,r,c)
                with self.subTest(file=path.name):
                    result=audit_file(path,brute_cells=16,transfer_width=6)
                    self.assertEqual(result.status,"PASS")
                    self.assertEqual(result.brute_force,"PASS")
                    self.assertEqual(result.fingerprints,"PASS_2_modular_probes")
                    self.assertEqual(len(result.sha256),64)

    def test_malformed_missing_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"2.3.csv"
            write_grid(path,2,3,sentinel=False)
            with self.assertRaisesRegex(AuditError,".DONE."):
                audit_file(path)

    def test_third_moment_catches_mutation_preserving_first_three(self):
        # Finite difference of order 3 annihilates polynomials in a of degree <3.
        # Thus total count, mean and second moment remain identical!
        changes = {(5,a):v for a,v in enumerate([-1,3,-3,1])}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"4.4.csv"
            write_grid(path,4,4,changes)
            with self.assertRaisesRegex(AuditError,"Moment order 3 FAILED"):
                audit_file(path,brute_cells=0,transfer_width=0)

    def test_naive_transfer_catches_mutation_preserving_moments_zero_to_three(self):
        # Finite difference of order 4 annihilates the four checked moments.
        changes = {(5,a):v for a,v in enumerate([-1,4,-6,4,-1])}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"4.4.csv"
            write_grid(path,4,4,changes)
            with self.assertRaisesRegex(AuditError,"fingerprint"):
                audit_file(path,brute_cells=0,transfer_width=6)

    def test_brute_force_catches_a_mutation_preserving_moments(self):
        changes = {(5,a):v for a,v in enumerate([-1,4,-6,4,-1])}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"4.4.csv"
            write_grid(path,4,4,changes)
            with self.assertRaisesRegex(AuditError,"brute-force mismatch"):
                audit_file(path,brute_cells=16,transfer_width=0)

    def test_direct_transfer_agrees_with_bruteforce_polynomial(self):
        for r,c in [(1,3),(2,2),(2,4),(3,3),(3,4)]:
            entries=brute_counts(r,c)
            for prime,x,y in PROBES:
                with self.subTest(r=r,c=c,prime=prime):
                    expected=sum(count*pow(x,o,prime)*pow(y,a,prime)
                                 for (o,a),count in entries.items())%prime
                    self.assertEqual(naive_transfer_evaluation(r,c,x,y,prime),expected)


if __name__ == '__main__':
    unittest.main()
