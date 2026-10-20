#!/usr/bin/env python3
"""Check byte-identical modular tables against the original dense kernel.

Designed to finish quickly. Compiles dense reference separately and tests
small rectangles plus a larger width-10 example. Does not edit any CSV data.
"""
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent

def main():
    dense=HERE/'mrc_fast_transform_dense_reference'
    newer=HERE/'mrc_fast_transform'
    if not newer.exists():
        subprocess.run(['bash',str(HERE/'build.sh')],check=True)
    subprocess.run(['g++','-O3','-std=c++17','-DNDEBUG','-march=native',
                    str(HERE/'mrc_fast_transform_dense_reference.cpp'),'-o',str(dense)],check=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        for r,c in [(1,1),(2,6),(3,5),(5,7),(7,9),(9,12),(10,12)]:
            for exe,name in [(dense,'dense'),(newer,'ragged')]:
                cmd=[str(exe),'--r',str(r),'--c',str(c),
                     '--mod','2147483647','--memory-gb','3',
                     '--algorithm','butterfly','--out',str(tmp/(name+'.mod'))]
                subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            assert (tmp/'dense.mod').read_bytes()==(tmp/'ragged.mod').read_bytes(),f'{r}x{c}'
            print(f'{r}x{c}: BYTE-FOR-BYTE MOD MATCH',flush=True)
    print('ALL DENSE/RAGGED COMPARISONS PASS')

if __name__=='__main__':main()
