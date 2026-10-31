#!/usr/bin/env python3
"""Independent fixed-occupancy lattice-gas thermodynamics regression tests."""
import csv
from collections import Counter
from decimal import Decimal
from math import comb, exp, log
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import mrc_data_statistics as mrc


def brute_configurations(r, c):
    """Enumerate actual cell configurations, not transfer tables or MRC polynomials."""
    n = r*c
    edges = [(i, i+1) for i in range(n) if i % c != c-1]
    edges += [(i, i+c) for i in range(n) if i+c < n]
    for mask in range(1 << n):
        occ = mask.bit_count()
        adj = sum(bool(mask & (1 << i)) and bool(mask & (1 << j)) for i,j in edges)
        yield occ, adj


def write_brute_table(path, r, c):
    n=r*c
    e=2*n-r-c
    counts=Counter(brute_configurations(r,c))
    with path.open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(('r','c','o','a','count'))
        for o in range(n+1):
            for a in range(e+1):
                writer.writerow((r,c,o,a,counts[o,a]))
        f.write('.DONE.\n')


def independent_gibbs(r,c,o,k,observed_a):
    # Each configuration is given weight exp(K*A), independent of the histogram.
    weights=[(a,exp(k*a)) for oo,a in brute_configurations(r,c) if oo==o]
    z=sum(w for a,w in weights)
    mu=sum(a*w for a,w in weights)/z
    var=sum((a-mu)**2*w for a,w in weights)/z
    observed=sum(w for a,w in weights if a==observed_a)/z
    return log(z), mu, var, k*k*var, observed


class TestThermodynamics(unittest.TestCase):
    def test_exact_low_dimensional_cases(self):
        cases=[(1,1,0),(1,3,2),(2,2,2),(2,3,3),(3,3,4)]
        for r,c,o in cases:
            counts=Counter(a for oo,a in brute_configurations(r,c) if oo==o)
            profile=mrc.prepare_distribution(r,c,o,dict(counts))
            for k in ['-2','-0.25','0','0.75','2']:
                observed=profile.amin
                z,mean,var,cv,p=independent_gibbs(r,c,o,float(k),observed)
                d=mrc.thermo_at_beta_j(profile,k,precision=35,observed_a=observed)
                self.assertAlmostEqual(float(d['log_partition_Z']),z,places=11)
                self.assertAlmostEqual(float(d['mean_couplings']),mean,places=11)
                self.assertAlmostEqual(float(d['variance_couplings']),var,places=11)
                self.assertAlmostEqual(float(d['heat_capacity_over_kB']),cv,places=11)
                self.assertAlmostEqual(float(d['observed_probability_at_beta_j']),p,places=11)
                if k=='0':
                    self.assertEqual(d['log_partition_Z_over_Z0'],'0')
                    self.assertEqual(d['heat_capacity_over_kB'],'0')
                    self.assertEqual(d['total_placements'],str(comb(r*c,o)))

    def test_closed_form_1x3_o2(self):
        p=mrc.prepare_distribution(1,3,2,{0:1,1:2})
        d=mrc.thermo_at_beta_j(p,'0',precision=40,observed_a=1)
        self.assertEqual(d['log_partition_Z_over_Z0'],'0')
        self.assertAlmostEqual(float(d['mean_couplings']),2/3,places=14)
        self.assertAlmostEqual(float(d['variance_couplings']),2/9,places=14)
        self.assertAlmostEqual(float(d['observed_probability_at_beta_j']),2/3,places=14)

    def test_strong_positive_and_negative_interactions(self):
        p=mrc.prepare_distribution(2,3,3,{a:w for a,w in Counter(
            a for oo,a in brute_configurations(2,3) if oo==3).items()})
        positive=mrc.thermo_at_beta_j(p,'10000',precision=30)
        negative=mrc.thermo_at_beta_j(p,'-10000',precision=30)
        self.assertEqual(Decimal(positive['mean_couplings']),Decimal(p.amax))
        self.assertLess(abs(Decimal(negative['mean_couplings'])-p.amin),Decimal('1e-30'))
        self.assertLess(Decimal(positive['heat_capacity_over_kB']),Decimal('1e-30'))
        self.assertLess(Decimal(negative['heat_capacity_over_kB']),Decimal('1e-30'))
        self.assertGreater(Decimal(positive['log_partition_Z']),0)

    def test_monotonicity_and_zero_limit(self):
        p=mrc.prepare_distribution(3,3,4,dict(Counter(
            a for oo,a in brute_configurations(3,3) if oo==4)))
        results=[mrc.thermo_at_beta_j(p,str(k),precision=40)
                 for k in [-4,-1,0,1,4]]
        means=[Decimal(x['mean_couplings']) for x in results]
        self.assertEqual(means,sorted(means))
        self.assertEqual(Decimal(results[2]['mean_couplings']),
                         Decimal(p.mean.numerator)/Decimal(p.mean.denominator))

    def test_cli_csv_json_orientation_and_old_single_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            write_brute_table(root/'2.3.csv',2,3)
            script=Path(mrc.__file__)
            def run(*args):
                return subprocess.run([sys.executable,str(script),*map(str,args)],
                                      text=True,capture_output=True)
            base=['3','2','3','--data-dir',str(root)]
            target=root/'thermo.csv'
            proc=run(*base,'--thermo','--beta-j','-2','--beta-j','0',
                     '--beta-j','1.25','--output',target,'--json')
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('"thermodynamics"',proc.stdout)
            with target.open() as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),3)
            self.assertEqual(rows[1]['log_partition_Z_over_Z0'],'0')
            self.assertEqual(rows[1]['r'],'3')
            self.assertEqual(rows[1]['c'],'2')
            self.assertEqual(rows[0]['beta_j'],'-2')
            self.assertEqual(rows[2]['beta_j'],'1.25')
            proc=run(*base,'1','--thermo','--beta-j','0')
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('P(A=1 | K)',proc.stdout)
            proc=run(*base,'1','--json')
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertIn('"probabilities"',proc.stdout)
            proc=run(*base,'--beta-j','2')
            self.assertEqual(proc.returncode,2)
            self.assertIn('requires --thermo',proc.stderr)
            proc=run(*base,'--thermo','--beta-j','NaN')
            self.assertEqual(proc.returncode,2)
            proc=run(*base,'--thermo','--beta-j','Infinity')
            self.assertEqual(proc.returncode,2)
            proc=run(*base,'--thermo','--output',root/'2.3.csv')
            self.assertEqual(proc.returncode,2)
            self.assertIn('Refusing to overwrite',proc.stderr)

if __name__=='__main__':
    unittest.main()
