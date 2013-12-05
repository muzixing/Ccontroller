
import errno
import functools
import tornado.ioloop as ioloop
import socket
import libopencflow as of
import stats_request as stats
import MySetting 

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
ready = 0
period = MySetting.period
count = 1
# dpid->type    
switch_info = {0:"ip", 1:"ip", 2:"wave", 3:"wave+ip",   4:"otn", 5:"otn+ip", 6:"otn+wave", 7: "wave+otn+ip"} # 1 otn; 2 otn->wave; 3 wave

# port->grain+slot(otn)/wave length(wave)
host_info = {           #odu0      #odu1    #odu2
                "otn":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "otn+ip":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "wave":{1:96, 2:95, 3:94}
            }
                
def handle_connection(connection, address):
        print "1 connection,", connection, address

def client_handler(address, fd, events):
    sock = fd_map[fd]
    if events & io_loop.READ:
        data = sock.recv(16384)
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
            if rmsg.type == 0:
                print "OFPT_HELLO"
                msg = of.ofp_header(type = 5)    #we send the features_request here.
                print "OFPT_FEATURES_REQUEST"
                io_loop.update_handler(fd, io_loop.WRITE)
                message_queue_map[sock].put(data)
                message_queue_map[sock].put(str(msg))
            elif rmsg.type == 1:
                print "OFPT_ERROR"
                of.ofp_error_msg(body).show()
  

            elif rmsg.type == 2:
                print "OFPT_ECHO_REQUEST"
                msg = of.ofp_header(type=3, xid=rmsg.xid)
                global exe_id 
                global ofp_match_obj
                
                message_queue_map[sock].put(str(msg))
                io_loop.update_handler(fd, io_loop.WRITE)
            elif rmsg.type == 3:
                print "OFPT_ECHO_REPLY"
            elif rmsg.type == 4:
                print "OFPT_VENDOR" #USE FOR WHAT?
            elif rmsg.type == 5:
                print "OFPT_FEATURES_REQUEST"
            elif rmsg.type == 6:
                print "OFPT_FEATURES_REPLY"
                msg = of.ofp_features_reply(body[0:24])                   #length of reply msg
                sock_dpid[fd]=[0, msg.datapath_id]                        #sock_dpid[fd] comes from here.
                global ready
                ready = 1                                                 #change the flag

                port_info_raw = str(body[24:])                            #we change it into str so we can manipulate it.
                port_info = {}
                print "port number:",len(port_info_raw)/48, "total length:", len(port_info_raw)
                for i in range(len(port_info_raw)/48):
                    port_info[i] = of.ofp_phy_port(port_info_raw[0+i*48:48+i*48])
                    print port_info[i].port_no   
            elif rmsg.type == 10:
                pkt_in_msg = of.ofp_packet_in(body)
                raw = pkt_in_msg.load
                pkt_parsed = of.Ether(raw)
                dpid = sock_dpid[fd][1]                                     #if there is not the key of sock_dpid[fd] ,it will be an error.
                
                if isinstance(pkt_parsed.payload, of.ARP):
                    
                    pkt_out_ = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
                    pkt_out_.payload.payload.port = 0xfffb
                    pkt_out_.payload.buffer_id = pkt_in_msg.buffer_id
                    pkt_out_.payload.in_port = pkt_in_msg.in_port
                    pkt_out_.payload.actions_len = 8
                    pkt_out_.length = 24
                    
                    io_loop.update_handler(fd, io_loop.WRITE)
                    message_queue_map[sock].put(str(pkt_out_))
                if isinstance(pkt_parsed.payload, of.IP) or isinstance(pkt_parsed.payload.payload, of.IP):   #sometimes, you need to send the flow_mod.
                    cflow_mod = of.ofp_header(type=0xff, xid=rmsg.xid)\
                                    /of.ofp_cflow_mod(command=0)\
                                    /of.ofp_connect_wildcards()\
                                    /of.ofp_connect(in_port = pkt_in_msg.in_port)\
                                    /of.ofp_action_output(type=0, port=0xfffb, len=8)
                        
                    type=switch_info[sock_dpid[fd][0]]
                    
                    if type == "otn":
                        grain=host_info[type][pkt_in_msg.in_port]
                        cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port
                        cflow_mod.payload.payload.payload.nport_out = 0xfffb
                        cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = grain[1]
                        cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = grain[0]
                    elif type == "otn+ip":
                        grain=host_info[type][pkt_in_msg.in_port]
                        cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port
                        cflow_mod.payload.payload.payload.nport_out = 0xfffb
                        cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = grain[1]
                        cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = grain[0]
                    elif type == "wave":
                        grain=host_info[type][pkt_in_msg.in_port]
                        cflow_mod.payload.payload.payload.wport_in = pkt_in_msg.in_port
                        cflow_mod.payload.payload.payload.wport_out = 0xfffb
                        cflow_mod.payload.payload.payload.num_wave_out = grain

                    message_queue_map[sock].put(str(cflow_mod))
                    io_loop.update_handler(fd, io_loop.WRITE)

                print "OFPT_BARRIER_REQUEST"
                msg = of.ofp_header(type = 18,xid = rmsg.xid) 
                message_queue_map[sock].put(str(msg))
                io_loop.update_handler(fd, io_loop.WRITE)
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
            elif rmsg.type == 17 and len(data)> 12:
                print "OFPT_STATS_REPLY"
                # 1. parsing ofp_stats_reply
                reply_header = of.ofp_stats_reply(body[:4])
                # 2.parsing ofp_flow_stats msg
                if reply_header.type == 0:
                    reply_desc = of.ofp_desc_stats(body[4:])
                    reply.show()
                elif reply_header.type == 1 and len(data)>92:
                    reply_body_data1 = of.ofp_flow_stats(body[4:8])
                    # match field in ofp_flow_stats
                    reply_body_wildcards = of.ofp_flow_wildcards(body[8:12])
                    reply_body_match = of.ofp_match(body[12:48])
                    # second part in ofp_flow_stats
                    reply_body_data2 = of.ofp_flow_stats_data(body[48:92])
                    # 3.parsing actions
                    reply_body_action = []
                    if len(body[92:])>8:                         #it is very important!
                        num = len(body[92:])/8
                        for x in xrange(num):
                            reply_body_action.append(of.ofp_action_output(body[92+x*8:100+x*8]))
                            
                    msg = reply_header/reply_body_data1/reply_body_wildcards/reply_body_match/reply_body_data2
                    msg.show()

                elif reply_header.type == 2:
                    reply_aggregate = of.ofp_aggregate_stats_reply(body[4:])
                    reply_aggregate.show()

                elif reply_header.type == 3:
                    #table_stats
                    length = rmsg.length - 12
                    num = length/64
                    for i in xrange(num):
                        table_body = body[4+i*64:i*64+68]
                        reply_table_stats = of.ofp_table_stats(table_body[:36])
                        table_wildcards = of.ofp_flow_wildcards(table_body[36:40])
                        reply_table_stats_data = of.ofp_table_stats_data(table_body[40:64])
                        msg_tmp = reply_header/reply_table_stats/table_wildcards/reply_table_stats_data
                    msg = rmsg/msg_tmp
                    msg.show() 
                elif reply_header.type == 4:
                    #port stats reply
                    length = rmsg.length - 12
                    num = length/104
                    for i in xrange(num):
                        offset = 4+i*104
                        reply_port_stats = of.ofp_port_stats_reply(body[offset:(offset+104)])
                        msg_tmp = reply_header/reply_port_stats
                    msg = rmsg/msg_tmp
                    msg.show()
                elif reply_header.type == 5:
                    #queue reply
                    length = rmsg.length - 12
                    num = length/32
                    if num:                     #if the queue is empty ,you need to check it !
                        for i in xrange(num):
                            offset = 4+i*32
                            queue_reply = of.ofp_queue_stats(body[offset:offset+32])
                            msg_tmp = reply_header/queue_reply
                        msg = rmsg/msg_tmp
                        msg.show()
                elif reply_header.type == 0xffff:
                    #vendor reply
                    msg = rmsg/reply_header/of.ofp_vendor(body[4:])

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
                
                ready = 1                               #change the flag
                msg = of.ofp_cfeatures_reply(body[0:24])
                
                #bind the dpid and type  (type,  dpid)

                Type = msg.OFPC_OTN_SWITCH*4 +msg.OFPC_WAVE_SWITCH*2 + msg.OFPC_IP_SWITCH
                
                sock_dpid[fd]=[Type, msg.datapath_id]
                
                port_info_raw = body[24:]            
                port_info = {}
                print "port number:",len(port_info_raw)/72, "total length:", len(port_info_raw)
                for i in range(len(port_info_raw)/72):
                    port_info[i] = of.ofp_phy_cport(port_info_raw[i*72:72+i*72])
                    print "port_no:",port_info[i].port_no,"i:",i


    global count
    if ready and count % period == 0:  
        print "send stats_requests"
        #request the stats per 3 seconds
        message_queue_map[sock].put(str(stats.send(1)))  #the parameter is the type of stats request
        io_loop.update_handler(fd, io_loop.WRITE)
        count = 1
    count+=1
                #------------------------------------------------------We finish the actions of manipulateing________________________

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