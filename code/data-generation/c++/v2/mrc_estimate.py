#!/usr/bin/env python3
"""Ragged butterfly peak RAM estimate (excludes OS, allocator and Python)."""
import argparse
from mrc_fast_generate import exact_primes
from mrc_batch_generate import ragged_entries

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r',type=int,required=True)
    parser.add_argument('--c',type=int,required=True)
    q=parser.parse_args()
    w,h=sorted((q.r,q.c))
    if w<=0 or w>=24:
        raise SystemExit('Need 1 <= min(r,c) <= 23')
    maskcount=1<<w
    previous=maskcount*(w+1)
    peak=0
    print(f'rectangle={w}x{h} modular_primes={len(exact_primes(w*h))}')
    print('row   current+next MiB   next-layer MiB')
    for row in range(1,h+1):
        nxt=maskcount*ragged_entries(w,row,h)
        two=(previous+nxt)*4/1048576
        if two>peak: peak=two
        if row==1 or row==h or row%5==0:
            print(f'{row:3}  {two:17,.1f}  {nxt*4/1048576:16,.1f}')
        previous=nxt
    print(f'Peak estimated C++ ragged arrays: {peak:,.1f} MiB = {peak/1024:.2f} GiB')
    print('Allow overhead and OS headroom; times and total system RAM are not predicted.')
if __name__=='__main__':
    main()
