import os
import sys
import socket
import select
import json
import logging

from socketserver import ThreadingTCPServer, StreamRequestHandler

CONFIG = 'config.json'
BUF_SIZE = 65536
(PROXY, PORT) = ('0.0.0.0', 9876)

# No obvious evidence that getfqdn slow down network speed
# socket.getfqdn = lambda x: x

def send_data(sock, data):
    total = 0
    while total < len(data):
        sent = sock.send(data[total:])
        if sent <= 0:
            raise RuntimeError('Error - broken socket')
        total += sent

class RemoteProxyServer(ThreadingTCPServer):
    allow_reuse_address = True

class RemoteRequestHandler(StreamRequestHandler):
    def handleTCP(self, local, dest):
        try:
            r_fdset = [local, dest]
            while True:
                rfds, _, _ = select.select(r_fdset, [], [])
                if local in rfds:
                    r_data = local.recv(BUF_SIZE)
                    if len(r_data) <= 0:
                        break
                    send_data(dest, r_data)
                if dest in rfds:
                    r_data = dest.recv(BUF_SIZE)
                    if len(r_data) <= 0:
                        break
                    send_data(local, r_data)
        except socket.error as e:
            logging.error(e)
        finally:
            local.close()
            dest.close()

    def handle(self):
        logging.info('Relay request from %r' % self.client_address[0])
        try:
            conn = self.connection
            r_data = conn.recv(BUF_SIZE)
            port = int.from_bytes(r_data[-2:], byteorder='big')
            atyp = r_data[0]
            if atyp == 1:
                address = socket.inet_ntoa(r_data[1: 5])
                logging.info('[address]: %r, [port]: %d' % (str(address, 'utf-8'), port))
            elif atyp == 3:
                l = r_data[1]
                address = r_data[2: 2 + l]
                logging.info('[address]: %r, [port]: %d' % (str(address, 'utf-8'), port))
            elif atyp == 4:
                pass
            else:
                logging.error('Not supported address type')
                return

            dest = socket.create_connection((address, port))
            self.handleTCP(conn, dest)
        except socket.error as e:
            logging.error(e)

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__) or '.')
    if os.path.exists(CONFIG):
        try:
            with open(CONFIG) as f:
                config = json.load(f)
            
            SERVER = config['server']
            SERVER_PORT = config['server_port']
            LOCAL = config['local']
            LOCAL_PORT = config['local_port']  
        except IOError:
            SERVER = '0.0.0.0'
            SERVER_PORT = 9876
            LOCAL = '127.0.0.1'
            LOCAL_PORT = '1080'
    else:
        SERVER = '0.0.0.0'
        SERVER_PORT = 9876
        LOCAL = '127.0.0.1'
        LOCAL_PORT = '1080'

    try:
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
        logging.info('Remote proxy starting...')
        proxy = RemoteProxyServer((SERVER, SERVER_PORT), RemoteRequestHandler)
        proxy.serve_forever()
    except socket.error as e:
        logging.error(e)
    except KeyboardInterrupt:
        proxy.shutdown()
        sys.exit(0)