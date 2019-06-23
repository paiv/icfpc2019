#!/usr/bin/env python
import multiprocessing
import os
import pathlib
import subprocess
import sys
import threading

import solver


def trace(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


def pworker(pargs):
    (infile, outfile, program, timeout, verbose) = pargs

    def tworker(infile, outfile):
        if verbose: trace(infile)
        w = solver.Worker(program)
        return w.solve(infile, outfile)

    t = threading.Thread(target=tworker, args=(infile, outfile))
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        if verbose: trace(f'timed out ({timeout} sec)')
        if not os.path.isfile(outfile):
            with open(outfile, 'w') as f: pass


def main(specdirs, program, targetdir, timeout=None, skip=False, skip_zero=False, verbose=False):
    def walk():
        for spec in specdirs:
            for fn in sorted(pathlib.Path(spec).glob('**/prob-*.desc')):
                tfn = os.path.join(targetdir, fn.with_suffix('.sol').name)
                fn = str(fn)

                if skip and os.path.isfile(tfn) and os.path.getsize(tfn):
                    continue
                if skip_zero and os.path.isfile(tfn) and os.path.getsize(tfn) == 0:
                    continue

                yield (fn, tfn, program, timeout, verbose)

    with multiprocessing.Pool() as pool:
        for _ in pool.imap_unordered(pworker, walk()):
            pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--program', nargs='?', default='greedy', help='Solver program')
    parser.add_argument('-r', '--targetdir', metavar='DIR', default='.', help='Target directory for solutions')
    parser.add_argument('-t', '--timeout', type=float, default=300, help='Solver timeout')
    parser.add_argument('-i', '--skip', action='store_true', help='Skip solved')
    parser.add_argument('-z', '--skip-zero', action='store_true', help='Skip timed out')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('specdir', metavar='SPEC', nargs='*', default='.', help='Directory with problems')
    args = parser.parse_args()

    main(args.specdir, args.program, args.targetdir,
        timeout=args.timeout,
        skip=args.skip,
        skip_zero=args.skip_zero,
        verbose=args.verbose)
