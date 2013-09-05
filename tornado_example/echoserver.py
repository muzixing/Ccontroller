import Queue
import socket
import libopenflow
from functools import partial
from tornado.ioloop import IOLoop

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setblocking(0)
server_address = ("localhost", 6733)
sock.bind(server_address)
sock.listen(5)

fd_map = {}              
message_queue_map = {}

fd = sock.fileno()
fd_map[fd] = sock

ioloop = IOLoop.instance()

def handle_client(cli_addr, fd, event):
    s = fd_map[fd]
    if event & IOLoop.READ:
        data = s.recv(1024)
        if data:
            print "     received '%s' from %s" % (data, cli_addr)
            ioloop.update_handler(fd, IOLoop.WRITE)
            message_queue_map[s].put(data)
        else:
            print "     closing %s" % cli_addr
            ioloop.remove_handler(fd)
            s.close()
            del message_queue_map[s]

    if event & IOLoop.WRITE:
        try:
            next_msg = message_queue_map[s].get_nowait()
        except Queue.Empty:
            print "%s queue empty" % cli_addr
            ioloop.update_handler(fd, IOLoop.READ)
        else:
            print 'sending "%s" to %s' % (next_msg, cli_addr)
            s.send(next_msg)

    if event & IOLoop.ERROR:
        print " exception on %s" % cli_addr
        ioloop.remove_handler(fd)
        s.close()
        del message_queue_map[s]


def handle_server(fd, event):
    s = fd_map[fd]
    if event & IOLoop.READ:
        conn, cli_addr = s.accept()
        print "     connection %s" % cli_addr[0]
        conn.setblocking(0)
        conn_fd = conn.fileno()
        fd_map[conn_fd] = conn
        handle = partial(handle_client, cli_addr[0])
        ioloop.add_handler(conn_fd, handle, IOLoop.READ)
        message_queue_map[conn] = Queue.Queue()


ioloop.add_handler(fd, handle_server, IOLoop.READ)
ioloop.start()
