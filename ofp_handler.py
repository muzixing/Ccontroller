import libopencflow as of
from scapy.all import *
import MySetting 

period = MySetting.period
sock_dpid = {}
fd_map = {}
features_info = {} 

# dpid->type    
switch_info = {0:"ip", 1:"ip", 2:"wave", 3:"wave+ip",   4:"otn", 5:"otn+ip", 6:"otn+wave", 7: "wave+otn+ip"} # 1 otn; 2 otn->wave; 3 wave

# port->grain+slot(otn)/wave length(wave)   no use!!
host_info = {           #odu0      #odu1    #odu2
                "otn":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "otn+ip":{1:(0,64), 2:(1,22), 3:(2,6), 4:(2,5)},
                "wave":{1:96, 2:95, 3:94}
            }
###########################################################################################

def hello_handler(body,*arg):
	print "OFPT_HELLO"
	msg = of.ofp_header(type = 5)    #we send the features_request here.
	print "OFPT_FEATURES_REQUEST"
	return msg

def error_handler(body, *arg):
	print "OFPT_ERROR"
	of.ofp_error_msg(body).show()
	return None

def echo_request_handler(rmsg,*arg):
	print "OFPT_ECHO_REQUEST"
	msg = of.ofp_header(type=3, xid=rmsg.xid)
	return msg

def echo_reply_handler(body,*arg):
	print "OFPT_ECHO_REPLY"
	return None

def vendor_handler(body,*arg):
	print "OFPT_VENDOR"
	return None

def features_request_handler(body,*arg):
	print "OFPT_FEATURES_REQUEST"
	return None

def features_reply_handler(body,*fd):
	msg = of.ofp_features_reply(body[0:24])                     #length of reply msg
	port_info_raw = str(body[24:])                              #we change it into str so we can manipulate it.
	port_info = {}

	print "port number:",len(port_info_raw)/48, "total length:", len(port_info_raw)
	for i in range(len(port_info_raw)/48):
	    port= of.ofp_phy_port(port_info_raw[0+i*48:48+i*48])
	    #port.show()
	    print port.port_no
	    port_info[port.port_no]= port                           #save port_info by port_no

	sock_dpid[fd]=[0, msg.datapath_id]                          #sock_dpid[fd] comes from here.
	features_info[msg.datapath_id] =(msg, port_info)            #features_info[dpid] = (sw_features, port_info{})

	return (msg,port_info)

def packet_in_handler(body,*fd):
	pkt_in_msg = of.ofp_packet_in(body)
	raw = pkt_in_msg.load
	pkt_parsed = of.Ether(raw)
	dpid = sock_dpid[fd][1]      #if there is not the key of sock_dpid[fd] ,it will be an error.

	if isinstance(pkt_parsed.payload, of.ARP):
		pkt_out_ = of.ofp_header()/of.ofp_pktout_header()/of.ofp_action_output()
		pkt_out_.payload.payload.port = 0xfffb
		pkt_out_.payload.buffer_id = pkt_in_msg.buffer_id
		pkt_out_.payload.in_port = pkt_in_msg.in_port
		pkt_out_.payload.actions_len = 8
		pkt_out_.length = 24
        
        return pkt_out_
	if isinstance(pkt_parsed.payload, of.IP) or isinstance(pkt_parsed.payload.payload, of.IP):
		cflow_mod = of.ofp_header(type=0xff, xid=rmsg.xid)\
					/of.ofp_cflow_mod(command=0)\
                    /of.ofp_connect_wildcards()\
                    /of.ofp_connect(in_port = pkt_in_msg.in_port)\
                    /of.ofp_action_output(type=0, port=0xfffb, len=8)

		type = switch_info[sock_dpid[fd][0]]        
		if type == "otn":
			cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port     #we need to add the in slot
			cflow_mod.payload.payload.payload.nport_out = 0xfffb                #we need to add the out slot
			cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].SUPP_SW_GRAN##change the in_port to out_port
			cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].sup_otn_port_bandwidth
		elif type == "otn+ip":
			cflow_mod.payload.payload.payload.nport_in = pkt_in_msg.in_port
			cflow_mod.payload.payload.payload.nport_out = 0xfffb
			cflow_mod.payload.payload.payload.supp_sw_otn_gran_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].SUPP_SW_GRAN
			cflow_mod.payload.payload.payload.sup_otn_port_bandwidth_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].sup_otn_port_bandwidth
		elif type == "wave":
			cflow_mod.payload.payload.payload.wport_in = pkt_in_msg.in_port
			cflow_mod.payload.payload.payload.wport_out = 0xfffb
			cflow_mod.payload.payload.payload.center_freq_lmda_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].payload.center_freq_lmda_out
			cflow_mod.payload.payload.payload.num_wave_out = features_info[sock_dpid[fd][1]][1][pkt_in_msg.in_port].payload.num_wave_out

		return cflow_mod

def barrier_handler(body,*arg):
	print "OFPT_BARRIER_REQUEST"
	msg = of.ofp_header(type = 18,xid = rmsg.xid) 
	return msg

def flow_removed_handler(body,*arg):
	print "OFPT_FLOW_REMOVED"
	return None

def port_status_handler(body,*arg):
	print "OFPT_PORT_STATUS"
	return None
def packet_out_handler(body,*arg):
	print "OFPT_PACKET_OUT"()
	return None

def flow_mod_handler(body, *arg):
	print "OFPT_FLOW_MOD"
	#we can do some thing here.
	return None

def port_mod_handler(body ,*arg):
	print "OFPT_PORT_MOD"
	return None

def status_request_handler(body, *arg):
	print "OFPT_STATS_REQUEST"
	return None

def status_reply_handler(body,*arg):
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
	return None

def barrier_request_handler(body,*arg):
	print "OFPT_BARRIER_REQUEST"
	#no message body, the xid is the previous barrier request xid
	return None

def barrier_reply_handler(body, *arg):
	print "OFPT_BARRIER_REPLY: ", rmsg.xid, "Successful"
	return None

def get_config_request_handler(body, *arg):
	print "OFPT_QUEUE_GET_CONFIG_REQUEST"
	#not finished yet.
	return None

def get_config_reply_handler(body,*arg):
	print "OFPT_QUEUE_GET_CONFIG_REPLY"
	#not finished yet
	return None

def cfeatrues_reply_handler(body,*arg):
	print "OFPT_CFEATURES_REPLY"
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

	return None

def send_stats_request_handler(Type, flow_1, port =None):
    flow =str(flow_1)
    ofp_flow_wildcards=of.ofp_flow_wildcards(flow[8:12])
    ofp_match =of.ofp_match(flow[12:48])
    ofp_flow_mod =of.ofp_flow_mod(flow[48:72])
    if len(flow)>=88:
        action_header = of.ofp_action_header(flow[72:80])
        action_output = of.ofp_action_output(flow[80:88])
    #we need to send the stats request packets periodically
    msg = { 0: of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 0),                            #Type of  OFPST_DESC (0) 
            1: of.ofp_header(type = 16, length = 56)/of.ofp_stats_request(type =1)/ofp_flow_wildcards/ofp_match/of.ofp_flow_stats_request(out_port = ofp_flow_mod.out_port),                  #flow stats
            2: of.ofp_header(type = 16, length =56)/of.ofp_stats_request(type = 2)/ofp_flow_wildcards/ofp_match/of.ofp_aggregate_stats_request(),                                  # aggregate stats request
            3: of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 3),                            #Type of  OFPST_TABLE (0) 
            4: of.ofp_header(type = 16, length =20)/of.ofp_stats_request(type = 4)/of.ofp_port_stats_request(port_no = port),   # port stats request    
            5: of.ofp_header(type = 16, length =20)/of.ofp_stats_request(type =5)/of.ofp_queue_stats_request(), #queue request
            6: of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 0xffff)                        #vendor request
        }
    return msg[Type]