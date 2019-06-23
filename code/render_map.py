#!/usr/bin/env python
import os
import re
import sys
from PIL import Image, ImageDraw


def trace(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


points_rx = re.compile(r',?\((\d+),(\d+)\)')

def parse_points(s):
    return [tuple(map(int, p)) for p in points_rx.findall(s)]


class Board:
    def load(f):
        desc = f.read()
        board, pos, obstacles, boosters = desc.split('#')
        board = parse_points(board)
        pos, = parse_points(pos)
        obstacles = [parse_points(x) for x in obstacles.strip().split(';') if x]
        boosters = [(x[0], parse_points(x[1:])[0]) for x in boosters.strip().split(';') if x]
        return Board(board, pos, obstacles, boosters)

    def __init__(self, board, pos, obstacles, boosters):
        self.board = board
        self.pos = pos
        self.obstacles = obstacles
        self.boosters = boosters
        self.size = (max(x for x,y in board), max(y for x,y in board))


class Puzzle:
    def load(f):
        data = f.read().split('#')
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


class Renderer:
    def __init__(self):
        self.booster_color = {
            'B': '#fecb45',
            'C': '#3a9bfc',
            'F': '#986515',
            'L': '#1fca23',
            'R': '#9373d8',
            'X': '#0b24fb',
        }

    def render_board(self, board, target_fn, cell_size=None):
        w, h = board.size
        if cell_size is None:
            cell_size = max(5, 800 // max(w, h))
            cell_size += (1 - cell_size % 2)
        w *= cell_size
        h *= cell_size

        with Image.new('RGB', (w+1, h+1), color='#f7f0e9') as im:
            draw = ImageDraw.Draw(im)

            def poly(path, outline, fill=None):
                px = [(x * cell_size, y * cell_size) for x,y in path]
                draw.polygon(px, outline=outline, fill=fill)

            def rect(at, r, outline, fill=None):
                x, y = at
                x, y = x * cell_size, y * cell_size
                r0, r1 = int(round((1 - r) / 2 * cell_size)), int(round((1 + r) / 2 * cell_size))
                px = [(x + r0, y + r0), (x + r1, y + r1)]
                draw.rectangle(px, outline=outline, fill=fill)

            def circle(at, r, outline, fill=None):
                x, y = at
                x, y = x * cell_size, y * cell_size
                r0, r1 = int(round((1 - r) / 2 * cell_size)), int(round((1 + r) / 2 * cell_size))
                px = [(x + r0, y + r0), (x + r1, y + r1)]
                draw.ellipse(px, outline=outline, fill=fill)

            def cells(cells, r, fill):
                w = (1 - r) * cell_size / 2
                for x, y in cells:
                    x, y = x * cell_size, y * cell_size
                    px = [((x + w), y + w), (x + cell_size - w, y + cell_size - w)]
                    draw.rectangle(px, outline=None, fill=fill)

            poly(board.board, '#8b8b8b', 'white')

            for p in board.obstacles:
                poly(p, '#333333', '#cccccc')

            px, py = board.pos
            cells([(px, py), (px+1, py), (px+1, py-1), (px+1, py+1)], 0.98, '#ecb229')

            for b, p in board.boosters:
                circle(p, 0.65, '#cccccc', self.booster_color[b])

            circle(board.pos, 0.34, '#cccccc', '#fc0d1b')

            im.transpose(Image.FLIP_TOP_BOTTOM).save(target_fn)

    def render_puzzle(self, puzzle, target_fn, cell_size=None):
        w, h = puzzle.size
        if cell_size is None:
            cell_size = max(5, 800 // max(w, h))
            cell_size += (1 - cell_size % 2)
        w *= cell_size
        h *= cell_size

        with Image.new('RGB', (w+1, h+1), color='#f7f0e9') as im:
            draw = ImageDraw.Draw(im)

            def rect(at, r, outline, fill=None):
                x, y = at
                x, y = x * cell_size, y * cell_size
                r0, r1 = int(round((1 - r) / 2 * cell_size)), int(round((1 + r) / 2 * cell_size))
                px = [(x + r0, y + r0), (x + r1, y + r1)]
                draw.rectangle(px, outline=outline, fill=fill)

            for p in puzzle.include_pos:
                rect(p, 1, '#8b8b8b', 'white')

            for p in puzzle.exclude_pos:
                rect(p, 1, '#333333', '#cccccc')

            im.transpose(Image.FLIP_TOP_BOTTOM).save(target_fn)


def main(infile, outfile):
    trace(infile.name)
    n, ext = os.path.splitext(infile.name)
    n = os.path.basename(n)

    if ext == '.desc':
        tx = 'task'
    elif ext == '.cond':
        tx = 'puzzle'
    else:
        raise Exception(ext)

    if not outfile:
        outfile = os.path.join('.', f'{n}-{tx}.png')
    trace(outfile)

    r = Renderer()

    if tx == 'task':
        board = Board.load(infile)
        r.render_board(board, outfile)
    elif tx == 'puzzle':
        puz = Puzzle.load(infile)
        r.render_puzzle(puz, outfile)
    else:
        raise Exception(tx)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument('outfile', nargs='?')
    args = parser.parse_args()

    main(args.infile, outfile=args.outfile)
