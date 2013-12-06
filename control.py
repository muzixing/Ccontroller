
from pox.core import core
import pox.openflow.libopenflow_01 as off
from pox.lib.revent import *
from pox.lib.recoco import *
import threading
import thread
from pox.lib.packet.ethernet import ethernet
from pox.lib.packet.arp import arp
from pox.lib.addresses import EthAddr, IPAddr

import struct
log = core.getLogger()

  
import errno
import functools
import tornado.ioloop as ioloop
import socket
import libopencflow as of
import stats_request as stats
import MySetting 

import Queue
import time


import tables
import route
import discovery as dc
create_topo = dc.Discovery()

message_queue_map = {}
global cookie
global exe_id # only for barrier
global ofp_match_obj
cookie = 0
exe_id = 0
ofp_match_obj = of.ofp_match()
ready = 0
period = MySetting.period
count = 1
s_type = 0#switch type
# dpid->type    
switch_info = {0:"ip", 1:"ip", 2:"wave", 3:"wave+ip",   4:"otn", 5:"otn+ip", 6:"otn+wave", 7: "wave+otn+ip"} # 1 otn; 2 otn->wave; 3 wave

# port->grain+slot(otn)/wave length(wave)
host_info = {           #odu0      #odu1    #odu2
                "otn":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "otn+ip":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "wave":{1:96, 2:95, 3:94}
            }

class Input (EventMixin,threading.Thread):
   """
   Suppose we have a component of our application that uses it's own event
   loop. recoco allows us to "add" our select loop to the other event
   loops running within pox.
   
   First note that we inherit from Task. The Task class is recoco's equivalent
   of python's threading.thread interface. 
   """
   def __init__(self):
     threading.Thread.__init__(self)
     print("here?")
     #Task.__init__(self)
     # Note! We can't start our event loop until the core is up. Therefore, 
     # we'll add an event handler.
     self.listenTo(core)

   def _handle_GoingUpEvent (self, event):
     """
     Takes a second parameter: the GoingUpEvent object (which we ignore)
     """ 
     # This causes us to be added to the scheduler's recurring Task queue
     self.start() 

   def run(self):
     while core.running:
       """
       This looks almost exactly like python's select.select, except that it's
       it's handled cooperatively by recoco
       
       The only difference in Syntax is the "yield" statement, and the
       capital S on "Select"
       """
       
       string = raw_input("1.info\n2.flow\n3.topo\n4.add link(add IP1,IP2,TYPE(BOTH=0, IP=1, OTN=2))?")
       string = string.split(' ')
       if string[0] == 'info':
         action = 1
         print tables.info_map
         print "\n\n\n"
       elif string[0] == 'flow':
         action = 2
         print tables.flow_map
         print "\n\n\n"
       elif string[0] == 'topo':
         action = 3
         print tables.topo_map
         print "\n\n\n"
       elif string[0] == 'add':
         action = 4
         s_type = string[1]
       elif string[0] == '0':
         print "stop input function...\n"
         return
       else:
         log.warning("Character string cannot be identified!")
         continue
       print action
       


#Ccontroller------def-----start
def handle_connection(connection, address):
  print "1 connection,", connection, address

def client_handler(address, fd, events):
  sock = tables.fd_map[fd]
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
      #rmsg.show()
      if rmsg.type == 0:
        print "OFPT_HELLO"
        msg = of.ofp_header(type = 5)#we send the features_request here.
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
        print "OFPT_VENDOR"

      elif rmsg.type == 5:
        print "OFPT_FEATURES_REQUEST"

      elif rmsg.type == 6:
        print "OFPT_FEATURES_REPLY"
        msg = of.ofp_features_reply(body[0:24])                   #length of reply msg
        tables.sock_dpid[fd]=[0, msg.datapath_id]                             #sock_dpid[fd] comes from here.
        global ready
        ready = 1                                                 #change the flag

        port_info_raw = str(body[24:])                            #we change it into str so we can manipulate it.
        port_info = {}
        print "port number:",len(port_info_raw)/48, "total length:", len(port_info_raw)
        for i in range(len(port_info_raw)/48):
          port_info[i] = of.ofp_phy_port(port_info_raw[0+i*48:48+i*48])
          print port_info[i].port_no     
                
      elif rmsg.type == 10:
        #print "OFPT_PACKET_IN"
        pkt_in_msg = of.ofp_packet_in(body)#buffer_id+in_port
        raw = pkt_in_msg.load
        pkt_ = ethernet(raw)
        pkt_parsed = of.Ether(raw)
        dpid = tables.sock_dpid[fd][1]
        if pkt_.effective_ethertype == 0x88cc:
          create_topo._handle_openflow_PacketIn(pkt_in_msg, pkt_, dpid)      
        elif pkt_.effective_ethertype == 0x0806:
          print "\n\nARP\n\n"
          request = pkt_parsed.next         
          if request.opcode == arp.REQUEST:
               reply = arp()
               reply.hwtype = request.hwtype
               reply.prototype = request.prototype
               reply.hwlen = request.hwlen
               reply.protolen = request.protolen
               reply.opcode = arp.REPLY
               reply.hwdst = request.hwsrc
               reply.protodst = request.protosrc
               reply.protosrc = request.protodst
               reply.hwsrc = tables.ip_mac[request.protodst]
               e_dpid = tables.sock_dpid[fd][1]
               for p,v in tables.switch_map[e_dpid]['port'].items():
                 if v.port_no == pkt_in_msg.in_port:
                   e_src = v.hw_addr
               e = ethernet(type = pkt_parsed.type, src = e_src, dst = pkt_parsed.src)
               e.set_payload(reply)
               msg = off.ofp_packet_out()
               msg.data = e.pack()
               msg.actions.append(off.ofp_action_output(port = off.OFPP_IN_PORT))#port problem
               msg.in_port = pkt_in_msg.in_port
               msg = msg.pack()

               io_loop.update_handler(fd, io_loop.WRITE)
               message_queue_map[sock].put(str(msg))
     
        elif pkt_.effective_ethertype == 0x0800:#0x0800
          print "\n\nIP\n\n"
          #dpid = tables.sock_dpid[fd][1]
          #src_mac = tables.switch_map[dpid]['port'][src_port].hw_addr
          #dst_mac = tables.switch_map[dpid]['port'][dst_port].hw_addr
          road, rlink, route_type = route.add_link(src, dst, s_type)
          if route_type == 0:
            header = of.ofp_header(type=14, length = 88, xid=rmsg.xid)
            wildcards = of.ofp_flow_wildcards(OFPFW_NW_TOS=1,      OFPFW_DL_VLAN_PCP=1,
                                              OFPFW_NW_DST_MASK=0, OFPFW_NW_SRC_MASK=0,
                                              OFPFW_TP_DST=1,      OFPFW_TP_SRC=1,
                                              OFPFW_NW_PROTO=1,    OFPFW_DL_TYPE=1,
                                              OFPFW_DL_DST=1,      OFPFW_DL_SRC=1,
                                              OFPFW_DL_VLAN=1,     OFPFW_IN_PORT=0)
            match = of.ofp_match(in_port=src_port, 
                                 dl_src=src_mac, dl_dst=dst_mac,
                                 nw_src=src_ip,  nw_dst=dst_ip)
            flow_mod = of.ofp_flow_mod(buffer_id = -1, idle_timeout = 0, flags = 1)
            action_header = of.ofp_action_header()
            action_output = of.ofp_action_output(port = dst_port)
      
            msg = header/wildcards/match/flow_mod/action_header/action_output
            message_queue_map[sock].put(str(msg))
            io_loop.update_handler(fd, io_loop.WRITE)

          else:
            cflow_mod = of.ofp_header(type=0xff, xid=rmsg.xid)\
                       /of.ofp_cflow_mod(command=0)\
                       /of.ofp_connect_wildcards()\
                       /of.ofp_connect(in_port = pkt_in_msg.in_port)\
                       /of.ofp_action_output(type=0, port=0xfffb, len=8)
            
            if route_type == 1:
              grain = host_info[type][pkt_in_msg.in_port]
              cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port
              cflow_mod.payload.payload.payload.nport_out = 0xfffb
              cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = grain[1]
              cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = grain[0]

            elif route_type == 2:
              grain = host_info[type][pkt_in_msg.in_port]
              cflow_mod.payload.payload.payload.wport_in = pkt_in_msg.in_port
              cflow_mod.payload.payload.payload.wport_out = 0xfffb
              cflow_mod.payload.payload.payload.num_wave_out = grain
            message_queue_map[sock].put(str(cflow_mod))
            io_loop.update_handler(fd, io_loop.WRITE)

          #print "OFPT_BARRIER_REQUEST"
          #msg = of.ofp_header(type = 18,xid = rmsg.xid) 
          #message_queue_map[sock].put(str(msg))
          #io_loop.update_handler(fd, io_loop.WRITE)

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
        msg = of.ofp_cfeatures_reply(body[0:24])#length of reply msg
        #bind the bpid and type  (type,  dpid)
         
        #WAVE:OTN:IP  b'000'
        if msg.OFPC_IP_SWITCH and (not (msg.OFPC_OTN_SWITCH or msg.OFPC_WAVE_SWITCH)):
          tables.sock_dpid[fd] = [1, msg.datapath_id]#IP only
        elif msg.OFPC_OTN_SWITCH and (not (msg.OFPC_IP_SWITCH or msg.OFPC_WAVE_SWITCH)):
          tables.sock_dpid[fd] = [2, msg.datapath_id]#OTN only
        elif msg.OFPC_WAVE_SWITCH and (not (msg.OFPC_OTN_SWITCH or msg.OFPC_IP_SWITCH)):
          tables.sock_dpid[fd] = [4, msg.datapath_id]#WAVE only
        elif msg.OFPC_IP_SWITCH and msg.OFPC_OTN_SWITCH and (not msg.OFPC_WAVE_SWITCH):
          tables.sock_dpid[fd] = [3, msg.datapath_id]#IP+OTN
        elif msg.OFPC_IP_SWITCH and msg.OFPC_WAVE_SWITCH and (not msg.OFPC_OTN_SWITCH):
          tables.sock_dpid[fd] = [5, msg.datapath_id]#IP+WAVE
        elif msg.OFPC_WAVE_SWITCH and msg.OFPC_OTN_SWITCH and (not msg.OFPC_IP_SWITCH):
          tables.sock_dpid[fd] = [6, msg.datapath_id]#WAVE+OTN
        elif msg.OFPC_IP_SWITCH and msg.OFPC_OTN_SWITCH and msg.OFPC_WAVE_SWITCH:
          tables.sock_dpid[fd] = [7, msg.datapath_id]#IP+OTN+WAVE
        port_info_raw = body[24:]
        port_info = {}
        port_i = {}
        print "port number:",len(port_info_raw)/72, "total length:", len(port_info_raw)
        for i in range(len(port_info_raw)/72):
          port_info[i] = of.ofp_phy_cport(port_info_raw[i*72:72+i*72])
          port_i[port_info[i].port_no] = port_info[i]
          #print "port_no:",port_info[i].port_no,"i:",i,"name:",port_info[i].port_name
          #print "\n\n"
          #print port_info[i].OFPST_T_OTN, "\t", port_info[i].OFPST_IP
        switch_type = tables.sock_dpid[fd][0]#features recorded in switch_map
        tables.switch_map[msg.datapath_id] = {'features':msg, 'type':switch_type, 'port':port_i}
           
        lldp_flow = create_topo._connection_up(msg.datapath_id)
        
        message_queue_map[sock].put(str(lldp_flow))
        io_loop.update_handler(fd, io_loop.WRITE)#discovery-handle
        
        create_topo._sender._connection_up(msg.datapath_id, port_info)
        #------------------------------------------------------We finish the actions of manipulateing___________________________

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
  tables.fd_map[connection.fileno()] = connection
  client_handle = functools.partial(client_handler, address)
  io_loop.add_handler(connection.fileno(), client_handle, io_loop.READ)
  print "in agent: new switch", connection.fileno(), client_handle
  message_queue_map[connection] = Queue.Queue()

def new_sock(block):
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setblocking(block)
  return sock
#Ccontroller------def-----end

#Ccontroller-----start
sock = new_sock(0)
sock.bind(("localhost", 6666))
sock.listen(6666)
	  
io_loop = ioloop.IOLoop.instance()
callback = functools.partial(agent, sock)
print sock, sock.getsockname()
io_loop.add_handler(sock.fileno(), callback, io_loop.READ)


try:
  thread.start_new_thread(io_loop.start,())
except KeyboardInterrupt:
  io_loop.stop()
  print "quit"
#Ccontroller-----end 


def launch ():
  core.registerNew(Input)
