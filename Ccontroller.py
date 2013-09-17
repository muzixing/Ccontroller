
import errno
import functools
import tornado.ioloop as ioloop
import socket
import libopencflow as of

import Queue
import time

sock_dpid = {}
fd_map = {}
message_queue_map = {}
pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_vlan_vid()/of.ofp_action_output()
global cookie
global exe_id # only for barrier
global ofp_match_obj
cookie = 0
exe_id = 0
ofp_match_obj = of.ofp_match()

# dpid->type
switch_info = {1:"otn", 2:"otn", 3:"wave"} # 1 otn; 2 otn->wave; 3 wave

# port->grain+slot(otn)/wave length(wave)
host_info = {           #odu0      #odu1    #odu2
                "otn":{1:(0,64), 2:(1,22), 3:(2,6)},
                "wave":{1:96, 2:95, 3:94}
            }
                

def handle_connection(connection, address):
        print "1 connection,", connection, address

def client_handler(address, fd, events):
    sock = fd_map[fd]
    #print sock, sock.getpeername(), sock.getsockname()
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
            #rmsg.show()
            if rmsg.type == 0:
                print "OFPT_HELLO"
                msg = of.ofp_header(type = 5)
                io_loop.update_handler(fd, io_loop.WRITE)
                message_queue_map[sock].put(data)
                message_queue_map[sock].put(str(msg))
            elif rmsg.type == 1:
                print "OFPT_ERROR"
                of.ofp_error_msg(body).show()
            elif rmsg.type == 6:
                print "OFPT_FEATURES_REPLY"
                #print "rmsg.load:",len(body)/48
                msg = of.ofp_features_reply(body[0:24])#length of reply msg
                sock_dpid[fd]=msg.datapath_id                                #sock_dpid[fd] comes from here.
                #msg.show()
                port_info_raw = str(body[24:])                             #we change it 
                port_info = {}
                print "port number:",len(port_info_raw)/48, "total length:", len(port_info_raw)
                for i in range(len(port_info_raw)/48):
                    port_info[i] = of.ofp_phy_port(port_info_raw[0+i*48:48+i*48])
                    print port_info[i].port_no     #show it

            elif rmsg.type == 2:
                print "OFPT_ECHO_REQUEST"
                msg = of.ofp_header(type=3, xid=rmsg.xid)
                
                #test for status request [which is good]
                global exe_id
                global ofp_match_obj
                
                message_queue_map[sock].put(str(msg))
                io_loop.update_handler(fd, io_loop.WRITE)
                
            elif rmsg.type == 10:
                #print "OFPT_PACKET_IN"
                pkt_in_msg = of.ofp_packet_in(body)
                raw = pkt_in_msg.load
                pkt_parsed = of.Ether(raw)
                dpid = sock_dpid[fd]
                
                if isinstance(pkt_parsed.payload, of.ARP):
                    
                    pkt_out_ = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                    pkt_out_.payload.payload.port = 0xfffb
                    pkt_out_.payload.buffer_id = pkt_in_msg.buffer_id
                    pkt_out_.payload.in_port = pkt_in_msg.in_port
                    pkt_out_.payload.actions_len = 8
                    pkt_out_.length = 24
                    
                    io_loop.update_handler(fd, io_loop.WRITE)
                    message_queue_map[sock].put(str(pkt_out_))
                if isinstance(pkt_parsed.payload, of.IP) or isinstance(pkt_parsed.payload.payload, of.IP):
                    if isinstance(pkt_parsed.payload.payload.payload, of.ICMP) or isinstance(pkt_parsed.payload.payload, of.ICMP):
                        cflow_mod = of.ofp_header(type=14, xid=rmsg.xid)\
                                    /of.ofp_cflow_mod(command=0)\
                                    /of.ofp_connect_wildcards()\
                                    /of.ofp_connect(in_port = pkt_in_msg.in_port)\
                                    /of.ofp_action_output(type=0, port=0xfffb, len=8)
                        
                        type=switch_info[sock_dpid[fd]]
                        grain=host_info[type][pkt_in_msg.in_port]
                        if type == "otn":
                            cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port
                            cflow_mod.payload.payload.payload.nport_out = 0xfffb
                            cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = grain[1]
                            cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = grain[0]
                        elif type == "wave":
                            cflow_mod.payload.payload.payload.wport_in = pkt_in_msg.in_port
                            cflow_mod.payload.payload.payload.wport_out = 0xfffb
                            cflow_mod.payload.payload.payload.num_wave_out = grain
                        #cflow_mod.show()
                        message_queue_map[sock].put(str(cflow_mod))
                        io_loop.update_handler(fd, io_loop.WRITE)
                        
                    
                    """if sock_dpid[fd] == 1:
                        # from sw1
                        if pkt_in_msg.in_port == 2:
                            #from sw2 -> sw1
                        elif pkt_in_msg.in_port == 1:
                            #from host1 -> sw1
                    elif sock_dpid[fd] == 2:
                        # from sw2
                        if pkt_in_msg.in_port == 2:
                            #from sw1 -> sw2
                        elif pkt_in_msg.in_port == 1:
                            #from host2 -> sw2"""
                                
                    #nport_in=1, supp_sw_otn_gran_in=1, in_port=1

            elif rmsg.type == 11: 
                print "OFPT_FLOW_REMOVED"
            elif rmsg.type == 12:
                print "OFPT_PORT_STATUS"
            elif rmsg.type == 13:
                print "OFPT_PACKET_OUT"
            elif rmsg.type == 14:
                print "OFPT_FLOW_MOD"
            elif rmsg.type == 15:
                print "OFPT_PORT_MOD"
            elif rmsg.type == 16:
                print "OFPT_STATS_REQUEST"
                
            elif rmsg.type == 17:
                print "OFPT_STATS_REPLY"
                # 1. parsing ofp_stats_reply
                reply_header = of.ofp_stats_reply(body[:4])
                
                # 2.parsing ofp_flow_stats msg
                reply_body_data1 = of.ofp_flow_stats(body[4:8])
                # match field in ofp_flow_stats
                reply_body_wildcards = of.ofp_flow_wildcards(body[8:12])
                reply_body_match = of.ofp_match(body[12:48])
                # second part in ofp_flow_stats
                reply_body_data2 = of.ofp_flow_stats_data(body[48:92])
                
                # 3.parsing actions
                # should first judge action type 
                i = 0
                reply_body_action = []
                #print len(body[92:])
                while i<len(body[92:]):
                    if body[95+i:96+i]==0x08:
                        print "0x08"
                    i+=8
                    if body[95+i:96+i] == 0x08:
                        reply_body_action.append(of.ofp_action_output(body[92+i:100+i]))
                        #i+=8
                # 4.show msg
                msg = reply_header/reply_body_data1/reply_body_wildcards/reply_body_match/reply_body_data2
                msg.show()
                print reply_body_action
            
            # no message body
            elif rmsg.type == 18:
                print "OFPT_BARRIER_REQUEST"
            
            #no message body, the xid is the previous barrier request xid
            elif rmsg.type == 19:
                print "OFPT_BARRIER_REPLY: ", rmsg.xid, "Successful"
            elif rmsg.type == 20:
                print "OFPT_QUEUE_GET_CONFIG_REQUEST"
            elif rmsg.type == 21:
                print "OFPT_QUEUE_GET_CONFIG_REPLY"
            elif rmsg.type == 24:
                print "OFPT_CFEATURES_REPLY"
                #print "rmsg.load:",len(body)/48
                msg = ofc.ofp_cfeatures_reply(body[0:24])#length of reply msg
                sock_dpid[fd]=msg.datapath_id
                #msg.show()
                port_info_raw = body[24:]
                port_info = {}
                print "port number:",len(port_info_raw)/72, "total length:", len(port_info_raw)
                for i in range(len(port_info_raw)/72):
                    port_info[i] = ofc.ofp_phy_cport(port_info_raw[i*72:72+i*72])
                    print "port_no:",port_info[i].port_no,"i:",i

                #------------------------------------------------------JUST PRINT IST FIRST.

    if events & io_loop.WRITE:
        try:
            next_msg = message_queue_map[sock].get_nowait()
        except Queue.Empty:
            #print "%s queue empty" % str(address)
            io_loop.update_handler(fd, io_loop.READ)
        else:
            #print 'sending "%s" to %s' % (of.ofp_header(next_msg).type, address)
            sock.send(next_msg)

def agent(sock, fd, events):
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
    print "in agent: new switch", connection.fileno(), client_handle
    message_queue_map[connection] = Queue.Queue()

def new_sock(block):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setblocking(block)
    return sock

if __name__ == '__main__':
    sock = new_sock(0)
    sock.bind(("localhost", 6634))
    sock.listen(6634)
    
    io_loop = ioloop.IOLoop.instance()
    #callback = functools.partial(connection_ready, sock)
    callback = functools.partial(agent, sock)
    print sock, sock.getsockname()
    io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
    try:
        io_loop.start()
    except KeyboardInterrupt:
        io_loop.stop()
        print "quit"