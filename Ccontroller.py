import errno
import functools
import tornado.ioloop as ioloop
import socket
import libopencflow as of
import ofp_handler

import Queue
import time

fd_map = {}
message_queue_map = {}

global cookie
cookie = 0
global ready
ready = 0
count = 1
######################################################################################################################                
def handle_connection(connection, address):
        print "1 connection,", connection, address
def client_handler(address, fd, events):
    sock = fd_map[fd]
    if events & io_loop.READ:
        data = sock.recv(1024)
        if data == '':
            print "connection dropped"
            io_loop.remove_handler(fd)
        if len(data)<8:
            print "not a openflow message"
        else:
            if len(data)>8:
                rmsg = of.ofp_header(data[0:8])
                body = data[8:]
            else:
                rmsg = of.ofp_header(data)

            handler = { 0:ofp_handler.hello_handler(body),
                        1:ofp_handler.error_handler(body),
                        2:ofp_handler.echo_request_handler(rmsg),
                        3:ofp_handler.echo_reply_handler(body),
                        4:ofp_handler.echo_reply_handler(body),
                        5:ofp_handler.features_request_handler(body),
                        6:ofp_handler.features_request_handler(body),
                        7:ofp_handler.features_reply_handler(body,fd),
                        8:None,
                        9:None,
                        10:ofp_handler.packet_in_handler(body,fd),
                        11:ofp_handler.flow_removed_handler(body),
                        12:ofp_handler.port_status_handler(body),
                        13:ofp_handler.packet_out_handler(body),
                        14:ofp_handler.flow_mod_handler(body),
                        15:ofp_handler.port_mod_handler(body),
                        16:ofp_handler.status_request_handler(body),
                        17:ofp_handler.status_reply(body),#body
                        18:ofp_handler.barrier_request_handler(body),
                        19:ofp_handler.barrier_reply_handler(body),
                        20:ofp_handler.get_config_request_handler(body),
                        21:ofp_handler.get_config_reply_handler(body),
                        24:ofp_handler.cfeatrues_reply_handler(body) #body
                        }
            if rmsg.type == 6:
                (msg, port_info) = handler[6]
                global ready
                ready = 1
            elif rmsg.type == 24:
                (msg, port_info) = handler[24]
                ready = 1
            else:
                msg = handler[rmsg.type]

            message_queue_map[sock].put(str(msg))
            io_loop.update_handler(fd, io_loop.WRITE)
    global count
    if ready and count % period == 0:
        #print "send stats_requests"
        flow =of.ofp_header()/of.ofp_flow_wildcards()/of.ofp_match()/of.ofp_flow_mod()
        message_queue_map[sock].put(str(ofp_handler.send_stats_request_handler(1,flow)))  #the parameter is the type of stats request
        io_loop.update_handler(fd, io_loop.WRITE)
        count = 1
    count+=1

    #################################   We finish the actions of manipulateing  ################################

    if events & io_loop.WRITE:
        try:
            next_msg = message_queue_map[sock].get_nowait()
        except Queue.Empty:
            #print "%s queue empty" % str(address)
            io_loop.update_handler(fd, io_loop.READ)
        else:
            #print 'sending "%s" to %s' % (of.ofp_header(next_msg).type, address)
            sock.send(next_msg)

def connection_up(sock, fd, events):
    #print fd, sock, events
    try:
        connection, address = sock.accept()
    except socket.error, e:
        if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise
        return
    connection.setblocking(0)
    handle_connection(connection, address)
    fd_map[connection.fileno()] = connection
    client_handle = functools.partial(client_handler, address)
    io_loop.add_handler(connection.fileno(), client_handle, io_loop.READ)
    print "in connection_up: new switch", connection.fileno(), client_handle
    message_queue_map[connection] = Queue.Queue()

def new_sock(block):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(block)
    return sock

if __name__ == '__main__':
    sock = new_sock(0)
    sock.bind(("", 6633))
    sock.listen(6633)
    
    io_loop = ioloop.IOLoop.instance()
    #callback = functools.partial(connection_ready, sock)
    callback = functools.partial(connection_up, sock)
    print sock, sock.getsockname()
    io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()
        print "quit" 

        
    """
    if rmsg.hello:
        msg = ofp_handler.hello_handler()
    elif rmsg.type == 1:
        ofp_handler.error_handler(body)
    elif rmsg.type == 2:
        msg = ofp_handler.echo_request_handler(rmsg)
    elif rmsg.type == 3:
        msg = ofp_handler.echo_reply_handler()
    elif rmsg.type == 4:
        msg = ofp_handler.vendor_handler()
    elif rmsg.type == 5:
        msg = ofp_handler.features_request_handler()
    elif rmsg.type == 6:
        (msg,port_info) = ofp_handler.features_reply_handler(body,fd)
        global ready
        ready = 1     
    elif rmsg.type == 10:
        msg = ofp_handler.packet_in_handler(body,fd)
        barrier = ofp_handler.barrier_handler()
        message_queue_map[sock].put(str(barrier))
    elif rmsg.type == 11:
        msg = ofp_handler.flow_removed_handler()
    elif rmsg.type == 12:
        msg = ofp_handler.port_status_handler()
    elif rmsg.type == 13:
        msg = ofp_handler.packet_out_handler()
    elif rmsg.type == 14:
        msg = ofp_handler.flow_mod_handler()
    elif rmsg.type == 15:
        msg = ofp_handler.port_mod_handler()
    elif rmsg.type == 16:
        msg = ofp_handler.status_request_handler()
    elif rmsg.type == 17 and len(data)> 12:
        msg = ofp_handler.status_reply(body)
    elif rmsg.type == 18:
        msg = ofp_handler.barrier_request_handler()
    elif rmsg.type == 19:
        msg = ofp_handler.barrier_reply_handler()
    elif rmsg.type == 20:
        msg = ofp_handler.get_config_request_handler()
    elif rmsg.type == 21:
        msg = ofp_handler.get_config_reply_handler()
    elif rmsg.type == 24:
        msg = ofp_handler.cfeatrues_reply_handler(body)
    
        ready = 1
    """

