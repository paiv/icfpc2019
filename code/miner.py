#!/usr/bin/env python
import multiprocessing
import os
import pathlib
import random
import sys
import threading
import time
import traceback
from jsonrpc_requests import Server

import digger
import solver


def trace(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


_data_dir = os.path.join(os.path.dirname(__file__), '../data/blocks')


def dig_worker(infile, outfile):
    trace('digging')
    dig = digger.Digger()
    dig.solve(infile, outfile)


def sol_worker(infile, outfile, program='walker', timeout=(30*60)):

    def tworker(infile, outfile):
        trace('solving')
        w = solver.Worker(program)
        return w.solve(infile, outfile)

    t = threading.Thread(target=tworker, args=(infile, outfile))
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        trace(f'solver timed out ({timeout} sec)')


def solve(block):
    trace('solving block')

    block_dir = pathlib.Path(_data_dir).joinpath(str(block['block']))
    os.makedirs(str(block_dir), exist_ok=True)

    puzzle_fn = str(block_dir.joinpath('puzzle.cond').resolve())
    puzzle_sol_fn = str(block_dir.joinpath('puzzle-sol.desc').resolve())
    task_fn = str(block_dir.joinpath('task.desc').resolve())
    task_sol_fn = str(block_dir.joinpath('task.sol').resolve())

    with open(puzzle_fn, 'w') as f:
        f.write(block['puzzle'])
    with open(task_fn, 'w') as f:
        f.write(block['task'])

    dig = threading.Thread(target=dig_worker, args=(puzzle_fn, puzzle_sol_fn))
    dig.start()

    sol = multiprocessing.Process(target=sol_worker, args=(task_fn, task_sol_fn))
    sol.start()
    sol.join()

    dig.join(timeout=600)
    if dig.is_alive():
        trace(f'digger timed out')

    ans = dict(
        block=block['block'],
        task_sol_fn=task_sol_fn,
        puzzle_sol_fn=puzzle_sol_fn,
    )
    return ans


def main(port, force=False):
    server = Server(f'http://127.0.0.1:{port}')

    last_block = None

    while True:
        try:
            info = server.getblockchaininfo()
            trace(info)

            if info['block'] != last_block:
                needs_solve = (last_block is not None) or force
                trace('needs_solve?', needs_solve)

                if needs_solve:
                    block = server.getblockinfo(info['block'])
                    sol = solve(block)
                    trace('sol:', sol)
                    if sol:
                        trace('submit')
                        r = server.submit(sol['block'], sol['task_sol_fn'], sol['puzzle_sol_fn'])
                        trace(r)

                last_block = info['block']
        except:
            trace(traceback.format_exc())
            pass
        trace('idle')
        time.sleep(random.randint(15, 25))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force-first', action='store_true', help='Solve the block at the start')
    parser.add_argument('-p', '--port', default=8332, help='Server port')
    args = parser.parse_args()

    main(port=args.port, force=args.force_first)
