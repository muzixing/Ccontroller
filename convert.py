# convert from ofp -> ofcp
# or back from ofcp -> ofp

import libopenflow as of
import libopencflow as ofc

def of2ofc(msg, buffer, dpid):
    print "of->ofc converting"
    if isinstance(msg, of.ofp_header):#it is a of packet.
        if isinstance(msg.payload, of.ofp_packet_in):
            # Save the buffer_id from pkt_in message. As 1. of.pkt_out message needs buffer_id
            # 2. the in_port is only one kind of pkt, this method seems okay in linear or ring topo
            
            #only need the ofp_header()/ofp_packet_in() part of the msg
            print "packet in from port", msg.payload.in_port
            buffer[msg.payload.in_port] = msg.payload.buffer_id
            #print buffer_id
        if isinstance(msg.payload, of.ofp_flow_mod):
            #basic structure: of.ofp_header()/of.ofp_flow_wildcards()/of.ofp_match()/of.ofp_flow_mod()/other_ofp_actions()
            #select info from match (VLAN) and actions (just copy)
            print "1"
        if isinstance(msg.payload, of.ofp_features_reply):
            print"it is a ofp_features_reply packet!"
            #basic structure:0fc.ofp_header()/ofc.ofp_features_reply()/ofc.ofp_phy_cport()/sup_wave_port_bandwidth()[n] 
            #we select the right field to fix our new packet.
            #how to convert?
            #buffer_id, pkt = buffer[(msg.payload.payload.payload.in_port, msg.xid)]
            #del buffer[(msg.payload.payload.payload.in_port, msg.xid)]
            pkt_parsed = msg[8:32]
            port_info = msg[32:]
            port_num = len(port_info)/48    #we need to know how many ports.       
            phy_port = {}
            cphy_port = {}
            cfeatures_reply = ofc.cfeatures_reply(datapath_id = pkt_parsed.datapath_id,
                                                  n_buffers = pkt_parsed.n_buffers,
                                                  n_tables = pkt_parsed.n_tables
                                                  n_cports = port_num,
                                                  #features
                                                  OFPC_OTN_SWITCH = pkt_parsed.OFPC_OTN_SWITCH,#1<<31
                                                  OFPC_WAVE_SWITCH = pkt_parsed.OFPC_WAVE_SWITCH,   #1<<30
                                                  NOT_DEFINED = pkt_parsed.NOT_DEFINED,
                                                  OFPC_ARP_MATCH_IP = pkt_parsed.OFPC_ARP_MATCH_IP,
                                                  OFPC_QUEUE_STATS = pkt_parsed.OFPC_QUEUE_STATS,  #1<<6 Queue statistics
                                                  OFPC_IP_STREAM = pkt_parsed.OFPC_IP_STREAM,     #1<<5 Can reassemble IP fragments
                                                  OFPC_RESERVED = pkt_parsed.OFPC_RESERVED,     #1<<4 Reserved, must be zero
                                                  OFPC_STP = pkt_parsed.OFPC_STP,         #1<<3 802.1d spanning tree
                                                  OFPC_PORT_STATS =pkt_parsed.OFPC_PORT_STATS,    #1<<2 Port statistics
                                                  OFPC_TABLE_STATS = pkt_parsed.OFPC_TABLE_STATS,  #1<<1 Table statistics
                                                  OFPC_FLOW_STATS = pkt_parsed.OFPC_FLOW_STATS,    #1<<0 Flow statistics
                                                  actions = pkt_parsed.actions)
            #cfeatures_reply has been built successfully
            for i in xrange(port_num):  #start from 0 or 1?
                phy_port[i] = of.ofp_phy_port(port_info[(i*48):(48+x*48)]) 
                print phy_port[i].port_no  
                cphy_port[i] =  ofc.ofp_phy_cport(port_no = phy_port[i].port_no,
                                                  hw_addr = phy_port[i].hw_addr,
                                                  port_name = phy_port[i].port_name,
                                                  config = phy_port[i].config,
                                                  state = phy_port[i].state,
                                                  curr = phy_port[i].curr,
                                                  advertised = phy_port[i].advertised,
                                                  supported = phy_port[i].supported,
                                                  peer = phy_port[i].peer,
                                                  #expend for circuit switch ports.
                                                  OFPST_FIBER = 0,   # 1<<15 can switch circuits based on SM/MM fiber
                                                  OFPST_WAVE = 0,     # 1<<14 can switch circuits based on ITU-T lambdas
                                                  OFPST_T_OTN = 0,    # 1<<13 can switch circuits based on OTN standard
                                                  OFPST_T_SDH = 0,  # 1<<12 can switch circuits based on SDH standard
                                                  OFPST_T_SONET = 0,  # 1<<11 can switch circuits based on SONET standard
                                                  NOT_DEFINED = 0,  # Not used
                                                  OFPST_ETH = 0,  # 1<<4 can switch packets based on ETH headers
                                                  OFPST_VLAN = 0,  # 1<<3 can switch packets based on VLAN tags
                                                  OFPST_MPLS = 0,  # 1<<2 can switch packets based on MPLS labels
                                                  OFPST_IP = 0,  # 1<<1 can switch packets based on IP headers 
                                                  OFPST_L4 = 0,  # 1<<0 can switch packets based on TCP/UDP headers

                                                  SUPP_SW_GRAN = 0,  #use for defined something ,waiting a second.
                                                  sup_sdh_port_bandwidth = 0,
                                                  sup_otn_port_bandwidth = 0,
                                                  peer_port_no = 0,
                                                  peer_datapath_id = 0)\
                                /ofc.sup_wave_port_bandwidth(center_freq_lmda = 0,
                                                             num_lmda = 0,
                                                             freq_space_lmda = 0
                                                             )
                cfeatures_reply =cfeatures_reply/cphy_port[i]   
                
            cfeatures_reply = ofc.ofp_header(type = 24, lenth =port_num*74+32,)/cfeatures_reply
            return cfeatures_reply
  #we should use for loop in here.

def ofc2of(msg, buffer, dpid):
    print "ofc->ofconverting"
    if isinstance(msg, ofc.ofp_header):
        if isinstance(msg.payload, ofc.ofp_cflow_mod):
            #self.buffer[(pkt_in_msg.in_port, id)] = [pkt_in_msg.buffer_id, rmsg/pkt_in_msg/pkt_parsed]
            #basic structure: ofp_header()/ofp_cflow_mod()/ofp_connect_wildcards()/ofp_connect()/other_ofp_actions()
            #select info from connect (port info) and actions (just copy)
            #WDM: num_wave -> vlan id
            #OTN: supp_sw_otn_gran->different map function ; bitmap->calculate vlan id
            #ODU0 = 0, ODU1 = 1 ...
            
            # [port + id] --> [buffer_id + pkt_in_msg]  
            #print buffer
            buffer_id, pkt = buffer[(msg.payload.payload.payload.in_port, msg.xid)]
            del buffer[(msg.payload.payload.payload.in_port, msg.xid)]
            pkt_parsed = pkt.payload.payload
            if isinstance(pkt_parsed.payload, of.IP) or isinstance(pkt_parsed.payload.payload, of.IP):
                    #print isinstance(pkt_parsed.payload, of.Dot1Q)
                    #print pkt_parsed.payload.vlan   
                    if isinstance(pkt_parsed.payload.payload.payload, of.ICMP):
                        #print "dpid:", sock_dpid[fd]
                        #pkt_parsed.show()
                        
                        flow_mod_msg = of.ofp_header(type=14,
                                                     length=88,)\
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
                                       /of.ofp_match(in_port=msg.payload.payload.payload.in_port,
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
                                       /of.ofp_flow_mod(cookie=0,
                                                        command=0,
                                                        idle_timeout=0,
                                                        hard_timeout=60,
                                                        buffer_id=buffer_id,#icmp type 8: request, 0: reply
                                                        flags=1)
                        
                        if msg.payload.payload.payload.nport_out:
                            port = msg.payload.payload.payload.nport_out
                        elif msg.payload.payload.payload.wport_out:
                            port = msg.payload.payload.payload.wport_out
                        if (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.1" and dpid == 2: # have VLAN and from node 2 -> 1 @s2 (rm vlan)
                            print "1->2 @s2"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_header(type=3)/of.ofp_action_output(type=0, port=port, len=8)
                        
                        elif (not isinstance(pkt_parsed.payload, of.IP)) and pkt_parsed.payload.src =="10.0.0.2" and dpid == 1: # have VLAN and from node 2 -> 1 (rm vlan)
                            print "1<-2 @s1"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_header(type=3)/of.ofp_action_output(type=0, port=port, len=8)
                        
                        #flow_mod_msg.show()
                        return flow_mod_msg
                    elif isinstance(pkt_parsed.payload.payload, of.ICMP):
                        
                        flow_mod_msg = of.ofp_header(type=14,
                                                     length=88,)\
                                       /of.ofp_flow_wildcards()\
                                       /of.ofp_match(in_port=msg.payload.payload.payload.in_port,
                                                     dl_src=pkt_parsed.src,
                                                     dl_dst=pkt_parsed.dst,
                                                     dl_type=pkt_parsed.type,
                                                     nw_tos=pkt_parsed.payload.tos,
                                                     nw_proto=pkt_parsed.payload.proto,
                                                     nw_src=pkt_parsed.payload.src,
                                                     nw_dst=pkt_parsed.payload.dst,
                                                     tp_src = pkt_parsed.payload.payload.type,
                                                     tp_dst = pkt_parsed.payload.payload.code)\
                                       /of.ofp_flow_mod(cookie=0,
                                                        command=0,
                                                        idle_timeout=0,
                                                        hard_timeout=60,
                                                        buffer_id=buffer_id,#icmp type 8: request, 0: reply
                                                        flags=1)
                        
                        if msg.payload.payload.payload.nport_out:
                            vid =  ofc2of_dict_odu[msg.payload.payload.payload.sup_otn_port_bandwidth_out](msg.payload.payload.payload.supp_sw_otn_gran_out)
                            port = msg.payload.payload.payload.nport_out
                        elif msg.payload.payload.payload.wport_out:
                            vid =  ofc2of_dict_wave(msg.payload.payload.payload.num_wave_out)
                            port = msg.payload.payload.payload.wport_out
                        # h1 -> (add vlan)of_switch(rm vlan) -> h2
                        if isinstance(pkt_parsed.payload, of.IP) and pkt_parsed.payload.src == "10.0.0.1" and dpid == 1: # not VLAN and from node 1 -> 2 @s1(add vlan)
                            print "1->2 @s1"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_vlan_vid(vlan_vid = vid)/of.ofp_action_output(type=0, port=port, len=8)                            
                        
                        # h1 <- (rm vlan)of_switch(add vlan) <- h2
                        elif isinstance(pkt_parsed.payload, of.IP) and pkt_parsed.payload.src == "10.0.0.2" and dpid == 2: # not VLAN and from node 1 -> 2 @s2(add vlan)
                            print "1<-2 @s2"
                            flow_mod_msg = flow_mod_msg/of.ofp_action_vlan_vid(vlan_vid = vid)/of.ofp_action_output(type=0, port=port, len=8)
                        #flow_mod_msg.show()
                        return flow_mod_msg
                            
buffer_id = {}

of2ofc_dict = {
               }

ofc2of_dict_odu = { 0: lambda x:x+2000,
                    1: lambda x:x+2100,
                    2: lambda x:x+2200,
                    3: lambda x:x+2300}

ofc2of_dict_wave = lambda x:x+3000
        
#of.ofp_header().show()
#ofc.ofp_header().show()

if __name__ == "__main__":
    # this convert (can) only match in-coming port and vlan
    
    # 1. packet_in message
    pkt_in_msg = of.ofp_header(type=14,length=88)/of.ofp_packet_in(in_port=1,buffer_id=128, total_len=10)
    #pkt_in_msg.show()
    of2ofc(pkt_in_msg, buffer_id) # get buffer_id
    
    ofc_pkt = ofc.ofp_header()\
          /ofc.ofp_cflow_mod()\
          /ofc.ofp_connect_wildcards()\
          /ofc.ofp_connect(nport_in=1, supp_sw_otn_gran_in=1, in_port=1)\
          /of.ofp_action_header(type=3)\
          /of.ofp_action_output(type=0, port=0xfffb, len=8)
    #ofc_pkt.show()
    print buffer_id
    # 2. parse ofc message
    of_pkt = ofc2of(ofc_pkt, buffer_id)
    
    # 3. print of message
    of_pkt.show()
    
    """
    print ofc2of_dict_odu[0](1)
    print ofc2of_dict_odu[0](30)
    print ofc2of_dict_odu[1](1)
    print ofc2of_dict_odu[2](1)
    print ofc2of_dict_odu[3](1)
    
    print ofc2of_dict_wave(80)
    """