#  i.
#  Request from client to negotiate auth method
#  +----+----------+----------+
#  |VER | NMETHODS | METHODS  |
#  +----+----------+----------+
#  | 1  |     1    | 1 to 255 |
#  +----+----------+----------+
#  3 common auth methods
#  X’00’ NO AUTHENTICATION REQUIRED
#  X’01’ GSSAPI
#  X’02’ USERNAME/PASSWORD
#  Response 
#  +----+--------+
#  |VER | METHOD |
#  +----+--------+
#  | 1  |    1   |
#  +----+--------+

# Based on RFC 1928, GSSAPI MUST be supported, and SHOULD support username/password authenticate methods

import socket
import select
import threading
import logging

from sys import exit
from socketserver import ThreadingTCPServer, StreamRequestHandler
from struct import unpack, pack

BUF_SIZE = 65536
(LOCAL, LOCAL_PORT) = ('127.0.0.1', 1080)
(REMOTE, REMOTE_PORT) = ('127.0.0.1', 9876)

LOCK = threading.Lock()
RUNNING_LOOPS = 0

def send_data(sock, data):
    total = 0
    while total < len(data):
        sent = sock.send(data[total:])
        if sent < 0:
            raise RuntimeError('Error - broken socket')
        total += sent

class LocalSocks5Server(ThreadingTCPServer):
    pass

class LocalRequestHandler(StreamRequestHandler):
    def handleTCP(self, local, remote):
        try:
            r_fdset = [local, remote]
            while True:
                rfds, _, _ = select.select(r_fdset, [], [])
                if local in rfds:
                    r_data = local.recv(BUF_SIZE)
                    if len(r_data) <= 0:
                        break
                    send_data(remote, r_data)
                if remote in rfds:
                    r_data = remote.recv(BUF_SIZE)
                    if len(r_data) <= 0:
                        break
                    send_data(local, r_data)
        finally:
            local.close()
            remote.close()

    def handle(self):
        global RUNNING_LOOPS
        LOCK.acquire()
        RUNNING_LOOPS += 1
        logging.info('Increasing running loops: [%d]' % RUNNING_LOOPS)
        LOCK.release()
        try:
            logging.info('Request from %r' % self.client_address[0])
            local = self.connection
            proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy.connect((REMOTE, REMOTE_PORT))
            # Authentication negotiate
            r_data = local.recv(BUF_SIZE)
            # support GSSAPI & user/password in the future
            local.send(b'\x05\x00')
            
            # Relay request
            r_data = local.recv(BUF_SIZE)
            cmd = r_data[1]
            atyp = r_data[3]
            # reply = b'\x05\x00\x00'
            if cmd == 1:
                # CONNECT CMD
                port = int.from_bytes(r_data[-2:], byteorder='big')
                if atyp == 1:
                    data = r_data[4: 8]
                    address = socket.inet_ntoa(data)
                    logging.info('[mode] CONNECT, [address]: %r, [port]: %r' % (str(address, 'utf-8'), port))
                elif atyp == 3:
                    l = r_data[4]
                    address = r_data[5: 5 + l]
                    logging.info('[mode] CONNECT, [address]: %s, [port]: %r' % (str(address, 'utf-8'), port))
                elif atyp == 4:
                    return
                else:
                    logging.error('Not supported address type')
                    return
                
                reply = b'\x05\x00\00' + r_data[3:]
                local.send(reply)
                proxy.send(r_data[3:])
            elif cmd == 3:
                # UDP ASSOCIATE
                pass
                return
            else:
                logging.error('Not supported command received')
                return
            logging.info('connecting remote %r:%r...' % (str(address, 'utf-8'), port))

            # remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # remote.connect((address, port))
            self.handleTCP(local, proxy)
        except socket.error as e:
            logging.error(e)
        finally:
            LOCK.acquire()
            RUNNING_LOOPS -= 1
            logging.info('Decreasing running loops: [%d]' % RUNNING_LOOPS)
            LOCK.release()


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
    logging.info('Local server starting...')
    try:
        local = LocalSocks5Server((LOCAL, LOCAL_PORT), LocalRequestHandler)
        local.serve_forever()
    except socket.error as e:
        logging.error(e)
    except KeyboardInterrupt:
        logging.info('Stopping local server...')
        LOCK.acquire()
        logging.info('Entering into critical zone...')
        if RUNNING_LOOPS > 0:
            logging.info('Running loops: [%d]' % RUNNING_LOOPS)
            local.shutdown()
        logging.info('Leaving away critical zone...')
        LOCK.release()
        exit(0)