import socket
import select
import os
import signal
import time
import sys
import subprocess
from subprocess import Popen, PIPE, DEVNULL


def test():
    try:
        l = Popen(['python3', 'local.py'], shell=True, bufsize=1, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        s = Popen(['python3', 'server.py'], shell=True, bufsize=1, stdout=PIPE, stdin=PIPE, stderr=PIPE)
        print('1 here')
        ready = 0
        t = None
        fdset = [l.stdout, l.stderr, s.stdout, s.stderr]
        while True:
            print('2 here')
            r_fdset, _, e_fdset = select.select(fdset, [], fdset)
            print('3 here')
            if e_fdset:
                print('Errors, quitting...')
                break

            if r_fdset:
                for r in r_fdset:
                    out = str(r.readline(), 'utf-8').rstrip()
                    print(out)
                    if out.find('starting...'):
                        ready += 1

            time.sleep(1)
            if ready == 2 and t is None:
                t = Popen(['curl', 'http://www.example.com/', '-v', '-L', '--socks5-hostname', '127.0.0.1:1080'], shell=False, bufsize=0, stdout=DEVNULL, close_fds=True)
                break

        if t is not None:
            print('waiting for test result...')
            r = t.wait()
            print('network request result code: %d' % r)
            if r == 0:
                print('test passed')
            else:
                print('test failed')
    finally:
        for p in [l, s]:
            try:
                os.kill(p.pid, signal.SIGTERM)
            except os.OSError as e:
                print(e)

if __name__ == '__main__':
    print('Test is running...')
    test()


