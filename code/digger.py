#!/usr/bin/env python
import heapq
import os
import random
import re
import sys
from collections import deque


def trace(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


class Puzzle:
    def load(f):
        return Puzzle.loads(f.read())

    def loads(s):
        data = s.split('#')
        (block, epoch, tsize, vmin, vmax, manipulators, wheels, drills, teleports, clonings, spawns) = map(int, data[0].split(','))
        include_pos = parse_points(data[1])
        exclude_pos = parse_points(data[2])
        return Puzzle(block, epoch, tsize, vmin, vmax, manipulators, wheels, drills, teleports, clonings, spawns, include_pos, exclude_pos)

    def __init__(self, block, epoch, tsize, vmin, vmax, manipulators, wheels, drills, teleports, clonings, spawns, include_pos, exclude_pos):
        self.block = block
        self.epoch = epoch
        self.tsize = tsize
        self.size = (tsize, tsize)
        self.vmin = vmin
        self.vmax = vmax
        self.manipulators = manipulators
        self.wheels = wheels
        self.drills = drills
        self.teleports = teleports
        self.clonings = clonings
        self.spawns = spawns
        self.include_pos = include_pos
        self.exclude_pos = exclude_pos


points_rx = re.compile(r',?\((\d+),(\d+)\)')

def parse_points(s):
    return [tuple(map(int, p)) for p in points_rx.findall(s)]


def dump_points(xs):
    return ','.join('({},{})'.format(p[0], p[1]) for p in xs)


def i2pos(p):
    return (int(p.real), int(p.imag))


class Board:
    def __init__(self, size):
        self.mine = None
        self.outline = list()
        self.pos = (0,0)
        self.boosters = list()
        self.size = size
        self.include_pos = None
        self.exclude_pos = None

    def save(self, fn):
        outline = dump_points(self.outline)
        pos = dump_points([self.pos])
        boost = ';'.join(t + dump_points([p]) for t, p in self.boosters)

        desc = '#'.join([outline, pos, '', boost])
        with open(fn, 'w') as f:
            f.write(desc)


class LoopError(Exception): pass


class Generator:
    def generate(self, puzzle):
        board = Board(size=puzzle.size)
        while True:
            try:
                self._build_mine(board, puzzle)
                break
            except LoopError:
                trace('** looped')
        self._scatter_objects(board, puzzle)
        return board

    def _build_mine(self, board, puzzle):
        mine = self._dig_holes(puzzle)
        outline = self._outline(mine)
        while not (puzzle.vmin <= len(outline) <= puzzle.vmax):
            mine = self._spread_darkness(mine, len(outline), puzzle)
            outline = self._outline(mine)
            if len(outline) > puzzle.vmax:
                trace('** overdig', len(outline), 'max:', puzzle.vmax)
                exit(1)
        board.mine = mine
        board.outline = outline

    def _dig_holes(self, puzzle):
        xpos = {(p[0] + 1j * p[1]) for p in puzzle.exclude_pos}
        ipos = {(p[0] + 1j * p[1]) for p in puzzle.include_pos}
        bounds = puzzle.tsize
        xgrid = set()

        for y in [-1, bounds]:
            for x in range(-1, bounds + 1):
                xgrid.add(x + 1j * y)
        for x in [-1, bounds]:
            for y in range(-1, bounds + 1):
                xgrid.add(x + 1j * y)

        def find_path(origin, goal):
            origin = (origin.real, origin.imag)
            goal = (goal.real, goal.imag)

            fringe = [(0, origin, [origin])]
            visited = set()
            while fringe:
                _,p,path = heapq.heappop(fringe)
                if (p == goal) or (p in xgrid):
                    return [(p[0] + 1j * p[1]) for p in path]
                if p in visited: continue
                visited.add(p)
                for dx, dy in ((1,0), (-1,0), (0,1), (0,-1)):
                    qx = p[0] + dx
                    qy = p[1] + dy
                    if ((qx + 1j * qy) not in ipos):
                        score = len(path) + 1 + abs(goal[0] - qx) + abs(goal[1] - qy)
                        heapq.heappush(fringe, (score, (qx, qy), path + [(qx, qy)]))

            return []

        def connect1(p):
            t = puzzle.tsize
            t = min([
                (abs(0 - p.real), 0, (0 + 1j * p.imag)),
                (abs(t - p.real), 1, (t + 1j * p.imag)),
                (abs(0 - p.imag), 2, (p.real + 1j * 0)),
                (abs(t - p.imag), 3, (p.real + 1j * t)),
                ])[2]
            while t in ipos:
                t += (t / abs(t))
            xgrid.update(find_path(p, t))

        for pad in range(puzzle.tsize // 2 + 2):
            pending = set()
            for y in [pad, puzzle.tsize - pad - 1]:
                off = 1j * y
                for x in range(pad, puzzle.tsize - pad):
                    p = off + x
                    if p in xpos:
                        pending.add(p)
            for x in [pad, puzzle.tsize - pad - 1]:
                off = x
                for y in range(pad, puzzle.tsize - pad):
                    p = off + 1j * y
                    if p in xpos:
                        pending.add(p)

            for p in random.sample(pending, len(pending)):
                connect1(p)

        return xgrid

    def _spread_darkness(self, mine, n, puzzle):
        ipos = {(p[0] + 1j * p[1]) for p in puzzle.include_pos}
        bounds = puzzle.tsize
        grid = set((x+1j*y) for y in range(-1, bounds+1) for x in range(-1, bounds+1))
        mvs = (1, -1j, -1, 1j)

        def walkcc(origin, mine):
            t = origin in mine
            fringe = deque([origin])
            visited = set()
            cc = set()
            while fringe:
                p = fringe.popleft()
                if p in visited: continue
                visited.add(p)
                cc.add(p)
                for i in mvs:
                    q = p + i
                    if (q in mine) == t:
                        fringe.append(q)
            return cc

        def cccn(mine):
            bs = walkcc(random.sample(mine, 1)[0], mine)
            ws = walkcc(random.sample(ipos, 1)[0], mine)
            return len(bs) + len(ws)

        xcc = cccn(mine)

        def dig1(mine):
            p, = random.sample(mine, 1)
            for i in mvs:
                q = p + i
                if q in mine:
                    p = q
                elif q in grid:
                    x = cccn(mine | {q})
                    if x == xcc:
                        mine.add(q)
                    return

        for _ in range((puzzle.vmin - n) // 2):
            dig1(mine)
        return mine

    def _outline(self, mine):
        origin = 0
        while origin in mine:
            origin += 1
        p = origin
        d = 1
        outline = [p]
        visited = {p}
        sqx = {1: -1j, 1j: 0, -1: -1, -1j: -1-1j}
        while True:
            q = p + d
            if q == origin: break
            sq1 = q + sqx[d]
            sq2 = q + sqx[d] * 1j - 1
            if sq1 not in mine:
                d *= -1j
                outline.append(q)
            elif sq2 in mine:
                d *= 1j
                outline.append(q)
            p = q
            if q in visited:
                # trace(dump_points([i2pos(x) for x in outline]))
                raise LoopError()
            visited.add(p)

        return [i2pos(x) for x in outline]

    def _scatter_objects(self, board, puzzle):
        visited = set()
        def rpos():
            while True:
                x = random.randrange(puzzle.tsize)
                y = random.randrange(puzzle.tsize)
                pos = (x, y)
                p = x + 1j * y
                if p in board.mine: continue
                if p in visited: continue
                visited.add(p)
                return pos
        def boost(t, n):
            return [(t, rpos()) for _ in range(n)]

        board.pos = rpos()
        mns = zip('BFLRCX', [puzzle.manipulators, puzzle.wheels, puzzle.drills, puzzle.teleports, puzzle.clonings, puzzle.spawns])
        board.boosters = [x for t, n in mns for x in boost(t, n)]


class Digger:
    def solve(self, infile, outfile=None):
        if isinstance(infile, str):
            with open(infile) as f:
                puz = Puzzle.load(f)
        else:
            puz = Puzzle.load(infile)
        gen = Generator()
        sol = gen.generate(puz)

        if not outfile:
            n, ext = os.path.splitext(infile.name)
            n = os.path.basename(n)
            outfile = os.path.join('.', f'{n}-sol.desc')

        sol.save(outfile)
        trace(outfile)


def main(infile, outfile=None):
    Digger().solve(infile, outfile)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('outfile', nargs='?')
    args = parser.parse_args()

    main(args.infile, args.outfile)
