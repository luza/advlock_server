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

    def get_list(self):
        return self.keys_storage

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
        self.locks = []
        self.commands = {
            'set': self.set_lock,
            'del': self.del_lock,
            'list': self.list_locks
        }

    def write_reply(self, code, message):
        self.write('%03d,%s\n' % (code, message))

    def set_version(self, version):
        self.version = version
        self.method = 'run_command'

    def run_command(self, command):
        cmd, sep, key = command.partition(' ')
        if cmd in self.commands:
            self.commands[cmd](key)
        else:
            self.write_reply(003, 'Unknown command')

    def set_lock(self, key):
        if not key:
            self.write_reply(002, 'Empty resource key')
            return
        value = self.storage.get(key)
        if value:
            self.write_reply(001, 'Resource already acquired by %s at %s' % (value['client_ip'],
                                                                             value['datetime']))
            return
        self.locks.append(key)
        self.storage.set(key, { "client_ip": '%s:%s' % (self.addr[0], self.addr[1]),
                                "version": self.version,
                                "datetime": datetime.datetime.now() })
        self.write_reply(000, 'OK')

    def del_lock(self, key):
        if not key:
            self.write_reply(002, 'Empty resource key')
            return
        if key not in self.locks:
            self.write_reply(004, 'Not a previously acquired resource')
            return
        self.locks.remove(key)
        self.storage.remove(key)
        self.write_reply(000, 'OK')

    def list_locks(self, unused):
        locks = self.storage.get_list()
        self.write_reply(000, 'OK %d records' % len(locks))
        for key, lock in locks.iteritems():
            self.write('%s\t%s\t%s\t%s\n' % (key, lock['datetime'], lock['client_ip'], lock['version']))

    # Data is ready for receiving from server
    def read(self, data):
        self.rbuf += data
        lines = self.rbuf.split('\n')
        if lines.count > 1:
            for line in lines[:-1]:
                method = getattr(self, self.method)
                method(line.strip())
            self.rbuf = lines[-1]

    # Send data to server
    def write(self, data):
        self.socket.send(data)

    # Connection closed
    def close(self):
        for key in self.locks:
            self.storage.remove(key)
        self.locks = []

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
        self.server_socket.setblocking(0) # Non-blocking
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

        # Check for connections ready to be accepted
        if self.server_socket in rlist:
            rlist.remove(self.server_socket)
            client_socket, addr = self.server_socket.accept()
            if client_socket:
                self.connection_objects[client_socket] = Connection(self.storage,
                                                                    client_socket,
                                                                    addr)

        # Processing reading events
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

