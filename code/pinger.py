#!/usr/bin/env python
import random
import subprocess
import sys
import time
from jsonrpc_requests import Server


def trace(*args, **kwargs):
    print(*args, file=sys.stderr, flush=True, **kwargs)


def main(port):
    server = Server(f'http://127.0.0.1:{port}')

    last_block = None

    while True:
        info = server.getblockchaininfo()
        trace(info)

        if info['block'] != last_block:
            last_block = info['block']

            notify_user('New block ' + str(last_block), title='ICFPC', sound='Basso')

        time.sleep(random.randint(15, 25))


def notify_user(text, title=None, sound=None):
    trace(text.strip())
    def x(s):
        s = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{s}"'

    script = f'display notification {x(text)}'
    if title:
        script += f' with title {x(title)}'
    if sound:
        script += f' sound name {x(sound)}'

    subprocess.run(['osascript', '-e', script])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', default=8332, help='Server port')
    args = parser.parse_args()

    main(port=args.port)
