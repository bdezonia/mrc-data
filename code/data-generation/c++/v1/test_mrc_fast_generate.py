#!/usr/bin/env python3
"""Unit / integration tests for exact generator, including independent brute force."""
from collections import defaultdict
from pathlib import Path
import csv
import subprocess
import sys
import tempfile

from mrc_fast_generate import exact_primes, generate, read_mod

BASE = Path(__file__).resolve().parent
KERNEL = BASE / 'mrc_fast_transform'


def brute(r, c):
    n = r*c
    edgebits = [(i,j) for i in range(n) for j in
                ([i+1] if i % c != c-1 else []) + ([i+c] if i < (r-1)*c else [])]
    out = defaultdict(int)
    for cells in range(1<<n):
        occupied = cells.bit_count()
        couplings = sum((cells>>i&1) and (cells>>j&1) for i,j in edgebits)
        out[occupied,couplings]+=1
    return out


def csv_counts(filename):
    out = {}
    with open(filename) as f:
        for row in csv.DictReader(line for line in f if not line.startswith('.DONE.')):
            v = int(row['count'])
            if v: out[int(row['o']),int(row['a'])] = v
    return out


def run_mod(r,c,p,algo,dest):
    subprocess.run([str(KERNEL),'--r',str(r),'--c',str(c),'--mod',str(p),
                    '--out',str(dest),'--algorithm',algo],check=True)


def test_all():
    if not KERNEL.exists():
        raise RuntimeError('compile first with ./build.sh')
    # Test all couplings, including boundaries, against independent enumeration.
    with tempfile.TemporaryDirectory() as t:
        temp = Path(t)
        for r,c in [(1,1),(1,6),(2,5),(3,4),(3,5),(4,4)]:
            target=temp/f'{r}.{c}.csv'
            generate(r,c,target,KERNEL,'butterfly',1.,False,False)
            a=csv_counts(target)
            b=brute(r,c)
            assert a==b,(r,c, {x:(a.get(x),b.get(x)) for x in (a.keys()|b.keys()) if a.get(x)!=b.get(x)})
            assert target.read_bytes().endswith(b'.DONE.\n')
            print(f'BRUTE EXACT {r}x{c} PASS')
        for r,c in [(4,7),(5,7),(6,7),(7,9)]:
            p=exact_primes(r*c)[0]
            f=temp/'fast.mod'; n=temp/'naive.mod'
            run_mod(r,c,p,'butterfly',f)
            run_mod(r,c,p,'naive',n)
            assert f.read_bytes()==n.read_bytes(),f'Naive/butterfly mismatch {r}x{c}'
            print(f'NAIVE MOD {r}x{c} PASS')
        # 35 cells requires >1 prime, tests correct CRT on nontrivial table.
        a=temp/'5.7.csv'
        generate(5,7,a,KERNEL,'butterfly',1.,False,False)
        b=temp/'5.7.naive.csv'
        generate(5,7,b,KERNEL,'naive',1.,False,False)
        assert a.read_bytes()==b.read_bytes(),'CRT reconstruction mismatch'
        print('CRT EXACT 5x7 PASS')
    print('ALL TESTS PASS')


if __name__=='__main__':
    test_all()
