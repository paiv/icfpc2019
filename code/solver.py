#!/usr/bin/env python
import ctypes
import os
import re
import sys
from collections import namedtuple


class Board:
    def load(f):
        desc = f.read()
        mine, pos, obstacles, boosters = desc.split('#')
        mine = parse_points(mine)
        pos, = parse_points(pos)
        obstacles = [parse_points(x) for x in obstacles.strip().split(';') if x]
        boosters = [(x[0], parse_points(x[1:])[0]) for x in boosters.strip().split(';') if x]
        return Board(mine, pos, obstacles, boosters)

    def __init__(self, mine, pos, obstacles, boosters):
        self.mine = mine
        self.pos = pos
        self.obstacles = obstacles
        self.boosters = boosters
        self.size = (max(x for x,y in mine), max(y for x,y in mine))

    def gen_grid(self):
        def flood(path):
            fringe = list()
            grid = set()
            for (ax, ay), (bx, by) in zip(path, path[1:] + path[:1]):
                a = 3 * (ax + 1j * ay)
                b = 3 * (bx + 1j * by)
                t = (b - a) / abs(b - a)
                while a != b:
                    d = a + t * (1 + 1j) / 2
                    x = int(d.real) + 1j * int(d.imag)
                    grid.add(x)
                    q = x + t * 1j
                    fringe.append(q)
                    a += t
            while fringe:
                p = fringe.pop()
                if p in grid: continue
                grid.add(p)
                for i in (1, -1, 1j, -1j):
                    q = p + i
                    fringe.append(q)
            return set((int(p.real / 3), int(p.imag / 3)) for p in grid)

        grid = flood(self.mine)
        obs = set()
        for x in self.obstacles:
            obs |= flood(x)

        return grid - obs


points_rx = re.compile(r',?\((\d+),(\d+)\)')

def parse_points(s):
    return [tuple(map(int, p)) for p in points_rx.findall(s)]


State = namedtuple('State', 'mine_size, pos, rotation, grid, boosters')


class CBooster(ctypes.Structure):
    _fields_ = [
        ('posx', ctypes.c_ushort),
        ('posy', ctypes.c_ushort),
        ('type', ctypes.c_char),
    ]

class CProblem(ctypes.Structure):
    _fields_ = [
        ('posx', ctypes.c_ushort),
        ('posy', ctypes.c_ushort),
        ('rotation', ctypes.c_ubyte),
        ('grid_size', ctypes.c_uint),
        ('grid', ctypes.POINTER(ctypes.c_ushort)),
        ('booster_size', ctypes.c_uint),
        ('boosters', ctypes.POINTER(CBooster)),
    ]


class Solver:
    def __init__(self, name='walker'):
        libname = f'{name}/build/release/lib{name}.dylib'
        libname = os.path.join(os.path.dirname(__file__), libname)
        self.bot = ctypes.cdll.LoadLibrary(libname)

    def solve(self, state):
        grid_t = ctypes.c_ushort * (2 * len(state.grid))
        grid = grid_t(*(x for p in state.grid for x in p))
        boost_t = CBooster * len(state.boosters)
        boosters = boost_t(*(
            CBooster(posx=x[1][0], posy=x[1][1], type=ord(x[0]))
            for x in state.boosters))

        cx = CProblem(
            posx=state.pos[0],
            posy=state.pos[1],
            rotation=state.rotation,
            grid_size=len(state.grid),
            grid=ctypes.cast(grid, ctypes.POINTER(ctypes.c_ushort)),
            booster_size=len(boosters),
            boosters=ctypes.cast(boosters, ctypes.POINTER(CBooster)),
            )

        ans_len = state.mine_size[0] * state.mine_size[1] * 2
        ans = (ctypes.c_char * ans_len)()
        r = self.bot.solve(ctypes.byref(cx), ans_len, ctypes.byref(ans))
        if r != 0:
            print('err', r, file=sys.stderr)
            return
        ans = ctypes.cast(ans, ctypes.c_char_p)
        return ans.value.decode('utf8')


class Worker:
    def __init__(self, program=None):
        self.program = program

    def solve(self, infile, outfile=None):
        if isinstance(infile, str):
            with open(infile) as f:
                board = Board.load(f)
        else:
            board = Board.load(infile)
        grid = board.gen_grid()

        state = State(mine_size=board.size, pos=board.pos, rotation=0, grid=grid, boosters=board.boosters)
        sol = Solver(name=self.program)
        ans = sol.solve(state)

        if not ans:
            return 1

        old = None
        if outfile and os.path.isfile(outfile):
            with open(outfile) as f:
                old = f.read().strip()

        if old and (len(old) <= len(ans)):
            return 0

        if outfile:
            with open(outfile, 'w') as f:
                f.write(ans)
        else:
            print(ans)

        return 0


def solve(infile, outfile=None, program=None):
    w = Worker(program)
    r = w.solve(infile, outfile)
    if r: exit(int(r))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--program', default='greedy', help='Solver program')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('outfile', nargs='?')
    args = parser.parse_args()

    solve(args.infile, outfile=args.outfile, program=args.program)
