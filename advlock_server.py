#!/usr/bin/env python

import socket
import select
import datetime
import sys

class KeysStorage:
    def __init__(self):
        self.keys_storage = {}

    def set(self, key, value):
        self.keys_storage[key] = value

    def remove(self, key):
        del self.keys_storage[key]

    def get(self, key):
        return self.keys_storage[key] if key in self.keys_storage else None

class TerminateConnectionException(Exception):
    pass

class Connection:
    def __init__(self, storage, socket, addr):
        self.socket = socket
        self.addr = addr
        self.rbuf = ''
        self.method = 'set_version'
        self.storage = storage
        self.version = ''
        self.key = ''

    def write_reply(self, code, message):
        self.write('%03d,%s\n' % (code, message))

    def set_version(self, version):
        self.version = version
        self.method = 'set_key'

    def set_key(self, key):
        if not key:
            self.write_reply(002, 'Empty key')
            raise TerminateConnectionException()
        value = self.storage.get(key)
        if value:
            self.write_reply(001, 'Resource already acquired by %s at %s' % (value['client_ip'],
                                                                             value['datetime']))
            raise TerminateConnectionException()
        self.key = key
        self.storage.set(key, { "client_ip": self.addr[0],
                                "version": self.version,
                                "datetime": datetime.datetime.now() })
        self.write_reply(000, 'OK')
        self.method = 'nop'

    def nop(self, value):
        pass

    def read(self, data):
        self.rbuf += data
        lines = self.rbuf.split('\n')
        if lines.count > 1:
            for line in lines[:-1]:
                method = getattr(self, self.method)
                method(line.strip())
            self.rbuf = lines[-1]

    def write(self, data):
        self.socket.send(data)

    def close(self):
        if self.key:
            self.storage.remove(self.key)

class Server:
    listen_backlog = 2
    rbufsize = 4096

    def __init__(self, addr, port):
        self.connection_objects = {}
        self.addr = addr
        self.port = port
        self.storage = KeysStorage()

    def start(self):
        self.server_socket = socket.socket()
        self.server_socket.setblocking(0) # non-blocking
        self.server_socket.bind((self.addr, self.port))
        self.server_socket.listen(self.listen_backlog)

        while True:
            self.process_events()

    def stop(self):
        for client_socket in self.connection_objects.keys():
            client_socket.close()
        self.server_socket.close()

    def process_events(self):
        rlist = [self.server_socket] + self.connection_objects.keys()
        rlist, wlist, xlist = select.select(rlist, [], [])

        # check for connections ready to be accepted
        if self.server_socket in rlist:
            rlist.remove(self.server_socket)
            client_socket, addr = self.server_socket.accept()
            if client_socket:
                self.connection_objects[client_socket] = Connection(self.storage,
                                                                    client_socket,
                                                                    addr)

        # processing reading events
        for client_socket in rlist:
            try:
                self.process_reading_event(client_socket)
            except (TerminateConnectionException, socket.error):
                client_socket.close()
                del self.connection_objects[client_socket]

    def process_reading_event(self, client_socket):
        data = client_socket.recv(self.rbufsize)
        if data:
            self.connection_objects[client_socket].read(data)
        else:
            self.connection_objects[client_socket].close()
            raise TerminateConnectionException()

def main():
    addr = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = sys.argv[2] if len(sys.argv) > 2 else 49915

    server = Server(addr, int(port))
    try:
        server.start()
    except:
        server.stop()
        raise

if __name__ == "__main__":
    main()

