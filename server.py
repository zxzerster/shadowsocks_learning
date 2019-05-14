from socketserver import ThreadingTCPServer, StreamRequestHandler
from socket import socket, AF_INET, SOCK_STREAM
from select import select

BUFF_SIZE = 4096

def send_data(sock, data):
    total = 0
    while total < len(data):
        sent = sock.send(data[total:])
        if sent == 0:
            raise RuntimeError('socket connection broken')
        total += sent

class MyServer(ThreadingTCPServer):
    pass

class MyRequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)
        self.local = None
        self.remote = None
    
    def handleTCP(self, local, remote):
        r_fdset = [local, remote]
        while True:
            r, _, _ = select(r_fdset, [], [])
            if local in r:
                data = local.recv(BUFF_SIZE)
                send_data(remote, data)
            if remote in r:
                data = remote.recv(BUFF_SIZE)
                send_data(local, data)

    def handle(self):
        print("Connecting from %r" % self.client_address[0])
        self.local = self.connection
        r_data = self.local.recv(BUFF_SIZE)
        print("[Handshake - phase 1]: reuqest - %r" % r_data)
        print("[Handshake - phase 1]: response - %r" % b'\x05\x00')
        self.local.send(b'\x05\x00')

        r_data = self.local.recv(BUFF_SIZE)
        print("[Handshake - phase 2]: reuqest - %r" % r_data)
        # mode = r_data[1]
        atyp = r_data[3]
        resp = b'\x05\x00\x00\x03'
        if atyp == 0x01:
            pass
        elif atyp == 0x03:
            addr_len = r_data[4]
            addr = r_data[5: 5 + addr_len]
            port = int.from_bytes(r_data[-2:], byteorder='big')
            print('[addr]: %s,  [port]: %d' % (str(addr, encoding='utf-8'), port))
            resp += r_data[4:]
            print('[Handshake - phase 2]: response - %r' % resp)
            self.local.send(resp)

            self.remote = socket(AF_INET, SOCK_STREAM)
            self.remote.connect((addr, port))
        else:
            pass
        
        self.handleTCP(self.local, self.remote)
        

if __name__ == '__main__':
    print("Starting server...")
    server = MyServer(('localhost', 9876), MyRequestHandler)
    server.serve_forever()