#!/usr/bin/env python3
"""Estimate memory needed for the MRC two-layer modular butterfly kernel."""
import argparse
from mrc_fast_generate import exact_primes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r',type=int,required=True)
    parser.add_argument('--c',type=int,required=True)
    q=parser.parse_args()
    w,h=sorted((q.r,q.c))
    if w<=0 or w>=24:
        raise SystemExit('Need 1 <= min(r,c) <= 23')
    maskcount=1<<w
    prev_entries=maskcount*(1)*(1+w)
    max_mib=0
    max_row=None
    print(f'rectangle={w}x{h} modular_primes={len(exact_primes(w*h))}')
    print('row   current+next MiB    next-layer MiB')
    for i in range(h):
        new_o=(i+1)*w
        new_a=(i+1)*(w-1)+i*w
        pad=w if i+1<h else 0
        next_entries=maskcount*(new_o+1)*(new_a+1+pad)
        twolayer=(prev_entries+next_entries)*4/1048576
        if twolayer>max_mib:
            max_mib, max_row=twolayer, i+1
        if i in (0,h-1) or (i+1)%5==0:
            print(f'{i+1:3}  {twolayer:17,.1f}  {next_entries*4/1048576:16,.1f}')
        prev_entries=next_entries
    print(f'Peak estimated C++ two-layer arrays: {max_mib:,.1f} MiB at row {max_row}.')
    print('Leave RAM headroom for OS, allocators and Python; CPU time is NOT estimated.')


if __name__=='__main__':
    main()
