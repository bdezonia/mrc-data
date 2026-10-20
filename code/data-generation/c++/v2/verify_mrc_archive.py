#!/usr/bin/env python3
"""Compare a newly generated MRC CSV to the original archive in a ZIP."""
import argparse
from pathlib import Path
from zipfile import ZipFile
import hashlib


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--csv',type=Path,required=True)
    parser.add_argument('--archive-name',help='override expected CSV basename in ZIP')
    args=parser.parse_args()
    name=args.archive_name or args.csv.name
    with ZipFile(args.archive) as z:
        matches=[file for file in z.namelist() if Path(file).name==name]
        if not matches:
            raise SystemExit(f'Archive does not contain {name}')
        if len(matches)>1:
            raise SystemExit(f'Ambiguous archive name {name}: {matches}')
        expected=z.read(matches[0])
    actual=args.csv.read_bytes()
    digest=hashlib.sha256(actual).hexdigest()
    print(f'file={name} bytes_archive={len(expected)} bytes_generated={len(actual)}')
    print(f'sha256_generated={digest}')
    if expected != actual:
        ix=next((i for i,(a,b) in enumerate(zip(expected,actual)) if a!=b),min(len(expected),len(actual)))
        raise SystemExit(f'MISMATCH: first differing byte index {ix}')
    print('BYTE-FOR-BYTE MATCH')


if __name__=='__main__':
    main()
