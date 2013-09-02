import errno
import functools
import tornado.ioloop as ioloop
import socket
import libopenflow as of

import Queue
import time

sock_dpid = {}
fd_map = {}
message_queue_map = {}
pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_vlan_vid()/of.ofp_action_output()
global cookie
global exe_id
global ofp_match_obj
cookie = 0
exe_id = 0
ofp_match_obj = of.ofp_match()

def handle_connection(connection, address):
        print "1 connection,", connection, address

def client_handler(address, fd, events):
    sock = fd_map[fd]
    #print sock, sock.getpeername(), sock.getsockname()
    if events & io_loop.READ:
        data = sock.recv(1024)
        if data == '':
            """
            According to stackoverflow(http://stackoverflow.com/questions/667640/how-to-tell-if-a-connection-is-dead-in-python)
            When a socket is closed, the server will receive a EOF. In python, however, server will
            receive a empty string(''). So, when a switch disconnected, the server will find out
            at once. But, if you do not react on this incident, there will be always a ``ioloop.read``
            event. And the loop will run forever, thus, the CPU useage will be pretty high.
            """
            print "connection dropped"
            io_loop.remove_handler(fd)
        if len(data)<8:
            print "not a openflow message"
        else:
            #print len(data)
            #if the data length is 8, then only of header
            #else, there are payload after the header
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
            elif rmsg.type == 5:
                print "OFPT_FEATURES_REQUEST"
            elif rmsg.type == 6:
                print "OFPT_FEATURES_REPLY"
                #print "rmsg.load:",len(body)/48
                msg = of.ofp_features_reply(body[0:24])#length of reply msg
                sock_dpid[fd]=msg.datapath_id
                #msg.show()
                port_info_raw = body[24:]
                port_info = {}
                print "port number:",len(port_info_raw)/48, "total length:", len(port_info_raw)
                for i in range(len(port_info_raw)/48):
                    #print "port", i, ",len:", len(port_info_raw[0+i*48:48+i*48]) 
                    """The port structure has a length of 48 bytes.
                       so when receiving port info, first split the list
                       into port structure length and then analysis
                    """
                    port_info[i] = of.ofp_phy_port(port_info_raw[0+i*48:48+i*48])
                    #print port_info[i].port_name
                    #port_info[i].show()
                    #print port_info[i].OFPPC_PORT_DOWN

            elif rmsg.type == 2:
                print "OFPT_ECHO_REQUEST"
                msg = of.ofp_header(type=3, xid=rmsg.xid)
                
                #test for status request [which is good]
                global exe_id
                global ofp_match_obj
                if exe_id>1:
                    #len = 8+4+44
                    stat_req = of.ofp_header(type=16,length=56)\
                               /of.ofp_stats_request(type=1)\
                               /of.ofp_flow_wildcards()\
                               /ofp_match_obj\
                               /of.ofp_flow_stats_request()
                    #stat_req.show()
                
                message_queue_map[sock].put(str(msg))
                #if exe_id>1:
                #    message_queue_map[sock].put(str(stat_req))
                io_loop.update_handler(fd, io_loop.WRITE)
                #end of test
                
                #io_loop.update_handler(fd, io_loop.WRITE)
                #message_queue_map[sock].put(str(msg))
            elif rmsg.type == 3:
                print "OFPT_ECHO_REPLY"
            elif rmsg.type == 4:
                print "OFPT_VENDOR"
            elif rmsg.type == 6:
                print "OFPT_FEATURES_REPLY"
            elif rmsg.type == 7:
                print "OFPT_GET_CONFIG_REQUEST"
            elif rmsg.type == 8:
                print "OFPT_GET_CONFIG_REPLY"
            elif rmsg.type == 9:
                print "OFPT_SET_CONFIG"
            elif rmsg.type == 10:
                #print "OFPT_PACKET_IN"
                #rmsg.show()
                pkt_in_msg = of.ofp_packet_in(body)
                raw = pkt_in_msg.load
                pkt_parsed = of.Ether(raw)
                
                
                #if sock_dpid[fd] == 2:
                #    print isinstance(pkt_parsed.payload, of.IP)
                #    pkt_parsed.payload.show()
                
                #pkt_parsed.show()
                #print "to see if the payload of ether is IP"
                #if isinstance(pkt_parsed.payload, of.IP):
                    #pkt_parsed.show()
                if isinstance(pkt_parsed.payload, of.ARP):
                    #pkt_parsed.show()
                    #pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                    pkt_out_ = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                    pkt_out_.payload.payload.port = 0xfffb
                    pkt_out_.payload.buffer_id = pkt_in_msg.buffer_id
                    pkt_out_.payload.in_port = pkt_in_msg.in_port
                    pkt_out_.payload.actions_len = 8
                    pkt_out_.length = 24
                    #pkt_out.show()
                    io_loop.update_handler(fd, io_loop.WRITE)
                    message_queue_map[sock].put(str(pkt_out_))
                if isinstance(pkt_parsed.payload, of.IP) or isinstance(pkt_parsed.payload.payload, of.IP):
                    #print isinstance(pkt_parsed.payload, of.Dot1Q)
                    #print pkt_parsed.payload.vlan
                    global cookie
                    global exe_id    
                    
                    if isinstance(pkt_parsed.payload.payload.payload, of.ICMP):
                        #print "dpid:", sock_dpid[fd]
                        rmsg.show()
                        pkt_in_msg.show()
                        pkt_parsed.show()
                        exe_id += 1
                        cookie += 1
                        
                        # when the wildcards bit is set (to 1), the field is not matched
                        flow_mod_msg = of.ofp_header(type=14,
                                                     length=88,
                                                     xid=exe_id)\
                                       /of.ofp_flow_wildcards(OFPFW_NW_TOS=1,
                                                              OFPFW_DL_VLAN_PCP=1,
                                                              OFPFW_NW_DST_MASK=1,
                                                              OFPFW_NW_SRC_MASK=1,
                                                              OFPFW_TP_DST=1,
                                                              OFPFW_TP_SRC=1,
                                                              OFPFW_NW_PROTO=1,
                                                              OFPFW_DL_TYPE=1,
                                                              OFPFW_DL_VLAN=0,
                                                              OFPFW_IN_PORT=0,
                                                              OFPFW_DL_DST=0,
                                                              OFPFW_DL_SRC=0)\
                                       /of.ofp_match(in_port=pkt_in_msg.in_port,
                                                     dl_src=pkt_parsed.src,
                                                     dl_dst=pkt_parsed.dst,
                                                     dl_type=pkt_parsed.type,
                                                     dl_vlan=pkt_parsed.payload.vlan,
                                                     nw_tos=pkt_parsed.payload.tos,
                                                     nw_proto=pkt_parsed.payload.proto,
                                                     nw_src=pkt_parsed.payload.src,
                                                     nw_dst=pkt_parsed.payload.dst,
                                                     tp_src = pkt_parsed.payload.payload.type,
                                                     tp_dst = pkt_parsed.payload.payload.code)\
                                       /of.ofp_flow_mod(cookie=cookie,
                                                        command=0,
                                                        idle_timeout=0,
                                                        hard_timeout=60,
                                                        buffer_id=pkt_in_msg.buffer_id,#icmp type 8: request, 0: reply
                                                        flags=1)
                        #! The match field is not right!
                        if (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.1" and sock_dpid[fd] == 2: # have VLAN and from node 2 -> 1 @s2 (rm vlan)
                            print "1->2 @s2"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_header(type=3)/of.ofp_action_output(type=0, port=0xfffb, len=8)
                        
                        elif (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.2" and sock_dpid[fd] == 1: # have VLAN and from node 2 -> 1 (rm vlan)
                            print "1<-2 @s1"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_header(type=3)/of.ofp_action_output(type=0, port=0xfffb, len=8)
                        
                        #flow_mod_msg.show()
                        io_loop.update_handler(fd, io_loop.WRITE)
                        #message_queue_map[sock].put(str(pkt_out))
                        message_queue_map[sock].put(str(flow_mod_msg))
                        message_queue_map[sock].put(str(of.ofp_header(type=18,xid=exe_id))) #send a barrier request msg.

                    elif isinstance(pkt_parsed.payload.payload, of.ICMP):
                        #print "dpid:", sock_dpid[fd]
                        #pkt_in_msg.show()
                        #pkt_parsed.show()
                        
                        #print "from", pkt_parsed.src, "to", pkt_parsed.dst 
                        
                        """
                        When receive a OPF_PACKET_IN message, you can caculate a path, and then
                        use OFP_FLOW_MOD message to install path. Also, you can find out the exact
                        port to send the message, then you can use the following code to send a
                        OFP_PACKET_OUT message and send the packet to destination.
                        """
                        
                        #pkt_parsed.show()
                        #pkt_out = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                        """pkt_out.payload.payload.vlan_vid = 100
                        pkt_out.payload.payload.payload.port = 0xfffb
                        pkt_out.payload.buffer_id = pkt_in_msg.buffer_id
                        pkt_out.payload.in_port = pkt_in_msg.in_port
                        pkt_out.payload.actions_len = 16
                        pkt_out.length = 32#24 with out vlan mod
                        pkt_out.show()"""
                        
                        """
                        io_loop.update_handler(fd, io_loop.WRITE)
                        message_queue_map[sock].put(str(pkt_out))
                        """
                        
                        #print pkt_parsed.payload.proto
                        #pkt_parsed.show()
                        #print "ICMP protocol"
                        #pkt_out.show()
                        #usually don't have to fill in ``wilecards`` area
                        
                        exe_id += 1
                        cookie += 1
                        
                        """flow_mod_msg = of.ofp_header(type=14,
                                                     length=80,
                                                     xid=exe_id)/\
                        of.ofp_flow_wildcards()\
                        /of.ofp_match(in_port=pkt_in_msg.in_port,
                                      dl_src=pkt_parsed.src,
                                      dl_dst=pkt_parsed.dst,
                                      dl_type=pkt_parsed.type,
                                      nw_tos=pkt_parsed.payload.tos,
                                      nw_proto=pkt_parsed.payload.proto,
                                      nw_src=pkt_parsed.payload.src,
                                      nw_dst=pkt_parsed.payload.dst,
                                      tp_src = pkt_parsed.payload.payload.type,
                                      tp_dst = pkt_parsed.payload.payload.code)\
                        /of.ofp_flow_mod(cookie=cookie,
                                         command=0,
                                         idle_timeout=60,
                                         buffer_id=pkt_in_msg.buffer_id,#icmp type 8: request, 0: reply
                                         flags=1)\
                        /of.ofp_action_output(type=0, 
                                              port=0xfffb,
                                              len=8)"""
                                              
                        flow_mod_msg = of.ofp_header(type=14,
                                                     length=88,
                                                     xid=exe_id)\
                                       /of.ofp_flow_wildcards()\
                                       /of.ofp_match(in_port=pkt_in_msg.in_port,
                                                     dl_src=pkt_parsed.src,
                                                     dl_dst=pkt_parsed.dst,
                                                     dl_type=pkt_parsed.type,
                                                     nw_tos=pkt_parsed.payload.tos,
                                                     nw_proto=pkt_parsed.payload.proto,
                                                     nw_src=pkt_parsed.payload.src,
                                                     nw_dst=pkt_parsed.payload.dst,
                                                     tp_src = pkt_parsed.payload.payload.type,
                                                     tp_dst = pkt_parsed.payload.payload.code)\
                                       /of.ofp_flow_mod(cookie=cookie,
                                                        command=0,
                                                        idle_timeout=0,
                                                        hard_timeout=60,
                                                        buffer_id=pkt_in_msg.buffer_id,#icmp type 8: request, 0: reply
                                                        flags=1)
                        
                        # h1 -> (add vlan)of_switch(rm vlan) -> h2
                        if isinstance(pkt_parsed.payload, of.IP) and pkt_parsed.payload.src == "10.0.0.1" and sock_dpid[fd] == 1: # not VLAN and from node 1 -> 2 @s1(add vlan)
                            print "1->2 @s1"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_vlan_vid(vlan_vid = 100)/of.ofp_action_output(type=0, port=0xfffb, len=8)                            
                        # second part in previous section(with 802.1q header)
                        #elif (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.1" and sock_dpid[fd] == 2: # have VLAN and from node 2 -> 1 @s2 (rm vlan)
                        #    print "1->2 @s2"
                        #    flow_mod_msg = flow_mod_msg/of.ofp_action_header(type=3)/of.ofp_action_output(type=0, port=0xfffb, len=8)
                       
                        # h1 <- (rm vlan)of_switch(add vlan) <- h2
                        elif isinstance(pkt_parsed.payload, of.IP) and pkt_parsed.payload.src == "10.0.0.2" and sock_dpid[fd] == 2: # not VLAN and from node 1 -> 2 @s2(add vlan)
                            print "1<-2 @s2"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_vlan_vid(vlan_vid = 200)/of.ofp_action_output(type=0, port=0xfffb, len=8)
                        #elif (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.2" and sock_dpid[fd] == 1: # have VLAN and from node 2 -> 1 (rm vlan)
                        #    print "1<-2 @s1"
                        #    flow_mod_msg = flow_mod_msg/of.ofp_action_output(type=0, port=0xfffb, len=8)/of.ofp_action_header(type=3)
                        
                        #flow_mod_msg.show()
                        """global ofp_match_obj
                        ofp_match_obj = of.ofp_match(in_port=pkt_in_msg.in_port,
                                      dl_src=pkt_parsed.src,
                                      dl_dst=pkt_parsed.dst,
                                      dl_type=pkt_parsed.type,
                                      nw_tos=pkt_parsed.payload.tos,
                                      nw_proto=pkt_parsed.payload.proto,
                                      nw_src=pkt_parsed.payload.src,
                                      nw_dst=pkt_parsed.payload.dst,
                                      tp_src = pkt_parsed.payload.payload.type,
                                      tp_dst = pkt_parsed.payload.payload.code)"""
                        
                        """
                        
                        print "--------------------------------------------------------------------------------------"
                        print "len of flow_mod_msg        :", len(str(flow_mod_msg))
                        print "len of of_header()         :", len(str(of.ofp_header()))
                        print "len of ofp_flow_wildcards():", len(str(of.ofp_flow_wildcards()))
                        print "len of ofp_match()         :", len(str(of.ofp_match()))
                        print "len of ofp_flow_mod()      :", len(str(of.ofp_flow_mod(command=0,idle_timeout=60,buffer_id=pkt_in_msg.buffer_id)))
                        print "len of ofp_action_output() :", len(str(of.ofp_action_output(type=0,port=0xfffb,len=8)))
                        print "--------------------------------------------------------------------------------------"
                        """
                        io_loop.update_handler(fd, io_loop.WRITE)
                        #message_queue_map[sock].put(str(pkt_out))
                        message_queue_map[sock].put(str(flow_mod_msg))
                        message_queue_map[sock].put(str(of.ofp_header(type=18,xid=exe_id))) #send a barrier request msg.

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
    sock.bind(("", 6634))
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