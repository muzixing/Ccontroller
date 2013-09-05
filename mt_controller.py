#import Queue
import select
import socket
import libopenflow as of
from functools import partial
from tornado.ioloop import IOLoop
import threading

fd_map = {}              
event_map = {}
thread_map = {}
pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()

class switch(threading.Thread):
    def __init__(self, sock, event):
        print "init for connection", sock.fileno()
        self.sock = sock # for sending pkts
        self.fd = sock.fileno()
        self.event = event # for waiting pkt_in
        self._quit = False
        super(switch, self).__init__()
    
    def send(self, pkt):
        select.select([], [self.sock], [])
        self.sock.send(pkt)
    
    def receive(self):
        select.select([self.sock], [], [])
        data = self.sock.recv(1024)
        return data
    
    def run(self):
        while not self._quit:
            #print "waiting", sock.getsockname()
            #sock.send("123")
            self.event.wait() #waiting for a packet
            if self._quit:
                print "receive quit signal"
                self.event.clear()
                return
            data = self.receive()
            #print 'sending "%s" to %s' % (of.ofp_header(next_msg).type, address)
            #data = self.receive()
            #print len(data), data
            if len(data)>=8:
                body = data[8:]
                msg = of.ofp_header(data)
                #msg.show()
                if msg.type == 0:
                    print "OFPT_HELLO"
                    msg = of.ofp_header(type = 5)
                    self.send(data)
                    self.send(str(msg))
                elif msg.type == 6:
                    print "OFPT_FEATURES_REPLY"
                    #feature = of.ofp_features_reply(body[0:24])
                    #feature.show()
                elif msg.type == 2:
                    print "OFPT_ECHO_REQUEST"
                    msg = of.ofp_header(type=3, xid=msg.xid)
                    self.send(str(msg))
                elif msg.type == 10:
                    #print "OFPT_PACKET_IN"
                    msg.show()
                    pkt_in_msg = of.ofp_packet_in(body)
                    #pkt_in_msg.show()
                    raw = pkt_in_msg.load
                    pkt_parsed = of.Ether(raw)
                    #pkt_parsed.payload.show()
                    #print "to see if the payload of ether is IP"
                    #if isinstance(pkt_parsed.payload, of.IP):
                        #pkt_parsed.show()
                    if isinstance(pkt_parsed.payload, of.ARP):
                        #pkt_parsed.show()
                        #pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                        pkt_out.payload.payload.port = 0xfffb
                        pkt_out.payload.buffer_id = pkt_in_msg.buffer_id
                        pkt_out.payload.in_port = pkt_in_msg.in_port
                        pkt_out.length = 24
                        #pkt_out.show()
                        self.send(str(pkt_out))
                    if isinstance(pkt_parsed.payload, of.IP):
                        if isinstance(pkt_parsed.payload.payload, of.ICMP):
                            #print "from", pkt_parsed.src, "to", pkt_parsed.dst 
                            pkt_out.payload.payload.port = 0xfffb
                            pkt_out.payload.buffer_id = pkt_in_msg.buffer_id
                            pkt_out.payload.in_port = pkt_in_msg.in_port
                            pkt_out.length = 24
                            self.send(str(pkt_out))
                #io_loop.stop()
                self.event.clear()
            #except 
            #data = ""
            elif data == "":
                print "close connection"
                self.stop()
                return
            else:
                self.send(data)
                self.event.clear()
        print "quit", self._quit

    def stop(self):
        print "closing thread & connection"
        print thread_map
        del thread_map[self.sock.fileno()]
        self.event.set()
        del event_map[self.sock.fileno()]
        print thread_map
        self.sock.close()
        self._quit = True

def handle_pkt(cli_addr, fd, event):
    if event & IOLoop.READ:
        #data = sock.recv(1024)
        if fd in event_map.keys():
            event_map[fd].set()
        #print s
        #ioloop.update_handler(fd, IOLoop.WRITE)
        #return
        
    if event & IOLoop.ERROR:
        print " exception on %s" % cli_addr
        io_loop.remove_handler(fd)
        fd_map[fd].close()
        #del message_queue_map[s]

def agent(sock, fd, events):
    #print fd, sock, events
    try:
        connection, address = sock.accept()
    except socket.error, e:
        if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise
        return
    connection.setblocking(0)
    connection_fd = connection.fileno()
    fd_map[connection_fd] = connection
    print "connection fd:", connection.fileno()
    client_handle = partial(handle_pkt, address)
    io_loop.add_handler(connection.fileno(), client_handle, io_loop.READ)
    print "in agent: new switch", connection.fileno(), client_handle
    event_map[connection_fd] = threading.Event()
    thread_map[connection_fd] = switch(connection, event_map[connection_fd])
    print thread_map
    thread_map[connection_fd].start()

def new_sock(block):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(block)
    return sock

if __name__ == '__main__':
    sock = new_sock(0)
    sock.bind(("", 6633))
    sock.listen(6633)
    fd = sock.fileno()
    fd_map[fd] = sock
    
    io_loop = IOLoop.instance()
    #callback = functools.partial(connection_ready, sock)
    callback = partial(agent, sock)
    print sock, sock.getsockname()
    io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
    try:
        io_loop.start()
    except KeyboardInterrupt:
        for i in thread_map.keys():
            thread_map[i].stop()
        io_loop.stop()
        print "quit"