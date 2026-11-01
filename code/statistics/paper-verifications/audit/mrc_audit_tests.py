#!/usr/bin/env python3
"""Independent generator audit: complete brute-force modular tests up to 16 cells.

Read-only to the archive. Requires the compiled kernel beside this script, or
use --kernel to specify it. Python 3.10+; standard library only.
"""
import argparse
from collections import defaultdict
from pathlib import Path
import struct
import subprocess
import tempfile
from math import comb


def brute(r,c):
    n=r*c
    edges=[(x,x+1) for x in range(n) if x%c !=c-1]
    edges += [(x,x+c) for x in range(n) if x+c<n]
    e=len(edges)
    result=[0]*((n+1)*(e+1))
    for bits in range(1<<n):
        o=bits.bit_count()
        a=sum(bool(bits>>u&1) and bool(bits>>v&1) for u,v in edges)
        result[o*(e+1)+a]+=1
    return result


def read_module(path,r,c,p):
    blob=path.read_bytes()
    n,e=r*c,2*r*c-r-c
    count=(n+1)*(e+1)
    assert len(blob)==28+4*count, (r,c,len(blob),count)
    assert struct.unpack('<8sIIIII',blob[:28])==(b'MRCMOD01',r,c,p,n,e)
    return struct.unpack('<'+str(count)+'I',blob[28:])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--kernel',type=Path,required=True,help='Path to a compiled mrc_fast_transform executable')
    args=ap.parse_args()
    k=args.kernel.resolve()
    if not k.is_file():
        ap.error(f'Please build kernel first: {k}')
    shapes=[(r,c) for r in range(1,5) for c in range(r,17) if r*c<=16]
    ps=(3,65537,2147483647)
    checked=0
    with tempfile.TemporaryDirectory() as temp:
        path=Path(temp)/'test.mod'
        for r,c in shapes:
            expected=brute(r,c)
            for p in ps:
                subprocess.run([str(k),'--r',str(r),'--c',str(c),'--mod',str(p),'--out',str(path)],check=True, stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                actual=read_module(path,r,c,p)
                assert list(actual)==[x%p for x in expected],f'mismatch: {r=} {c=} {p=}'
                checked+=1
            print(f'{r}x{c}: PASS all {len(ps)} moduli')
    print(f'AUDIT SUCCESS: {len(shapes)} rectangles, {checked} complete modular comparisons')

if __name__=='__main__':
    main()
