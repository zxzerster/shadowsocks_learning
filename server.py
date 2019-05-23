import sys
import socket
import select
import logging

from socketserver import ThreadingTCPServer, StreamRequestHandler

BUF_SIZE = 65536
(PROXY, PORT) = ('0.0.0.0', 9876)

def send_data(sock, data):
    total = 0
    while total < len(data):
        sent = sock.send(data[total:])
        if sent <= 0:
            raise RuntimeError('Error - broken socket')
        total += sent

class RemoteProxyServer(ThreadingTCPServer):
    pass

class RemoteRequestHandler(StreamRequestHandler):
    def handleTCP(self, local, dest):
        try:
            r_fdset = [local, dest]
            while True:
                rfds, _, _ = select.select(r_fdset, [], [])
                if local in rfds:
                    r_data = local.recv(BUF_SIZE)
                    send_data(dest, r_data)
                if dest in rfds:
                    r_data = dest.recv(BUF_SIZE)
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
            
            dest = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            dest.connect((address, port))
            self.handleTCP(conn, dest)
        except socket.error as e:
            logging.error(e)

if __name__ == '__main__':
    try:
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
        logging.info('Remote proxy starting...')
        proxy = RemoteProxyServer((PROXY, PORT), RemoteRequestHandler)
        proxy.serve_forever()
    except socket.error as e:
        logging.error(e)
    except KeyboardInterrupt:
        proxy.shutdown()
        sys.exit(0)