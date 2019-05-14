from socketserver import ThreadingTCPServer, StreamRequestHandler
from socket import socket, inet_ntoa, AF_INET, SOCK_STREAM
from struct import unpack, pack
from select import select

BUFF_SIZE = 4096

(SERVER, PORT) = ('localhost', 9876)

def send_data(sock, data):
    total = 0
    l = len(data)
    while total < l:
        sent = sock.send(data[total:])
        if sent <= 0:
            raise RuntimeError('socket connection broken')
        total += sent

class LocalProxy(ThreadingTCPServer):
    pass

class LocalRequestHandler(StreamRequestHandler):
    def handleTCP(self, local, server):
        r_fdset = [local, server]
        count = 0
        while True:
            r, _, _ = select(r_fdset, [], [])
            if local in r:
                r_data = local.recv(BUFF_SIZE)
                if count == 1:
                    mode = r_data[1]
                    atyp = r_data[3]
                    port = unpack('>H', r_data[-2:])
                    addr = None
                    if atyp == 1:
                        addr = inet_ntoa(r_data[4: 8])
                    elif atyp == 3:
                        addr_len = r_data[4]
                        addr = r_data[5: 5 + addr_len]
                    print('[mode]: %d' % mode)
                    print('[Connecting]: %r,  [port]: %r' % (addr, port))
                if count < 2:
                    ver = r_data[0]
                    print('[SOCKS ver required]: %r' % ver)
                    count += 1
                server.send(r_data)
                pass
            if server in r:
                r_data = server.recv(BUFF_SIZE)
                send_data(local, r_data)

    def handle(self):
        print('[Connection]: request from %r' % self.client_address[0])
        # create SOCKS5 server socket
        server = socket(AF_INET, SOCK_STREAM)
        server.connect((SERVER, PORT))
        local = self.connection
        self.handleTCP(local, server)

if __name__ == '__main__':
    proxy = LocalProxy(('127.0.0.1', 1234), LocalRequestHandler)
    proxy.serve_forever()