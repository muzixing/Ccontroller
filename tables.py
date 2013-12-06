topo_map = {}
#{(dpid1,port1,dpid2,port2):{'type':link_type, 'bandwidth':BW, "payload":PL, 'status':link_status, 'bit_map':map of slots}}

info_map = {}
#{(dpid1,port1,dpid2,port2):{slot_no:{'type':slot_type, 'service':slot_ser, 'status':slot_status}}}

flow_map = {}
service_map = {}

switch_map = {}
#{dpid:{'features':features_reply, 'type':switch_type, 'port':port_info}}

sock_dpid = {}
#{file_no:[switch_type, dpid]}

fd_map = {}
#{file_no:socket}

from pox.lib.addresses import EthAddr, IPAddr
ip_mac={IPAddr('10.0.0.1'):EthAddr('00:00:00:00:00:01'), 
        IPAddr('10.0.0.2'):EthAddr('00:00:00:00:00:02')}

ip_dpid_port = {'10.0.0.1':[1,1], '10.0.0.2':[3,2]}

MAX = 65535
route_map = [[MAX,MAX,MAX,MAX,MAX],
             [MAX,0,1,MAX,2],
             [MAX,1,0,1,MAX],
             [MAX,MAX,1,0,2],
             [MAX,2,MAX,2,0],]
'''
route_map = [[MAX,MAX,MAX,MAX,MAX,MAX],
             [MAX,0,10,MAX,30,100],
             [MAX,10,0,50,MAX,MAX],
             [MAX,MAX,50,0,20,10],
             [MAX,30,MAX,20,0,60],
             [MAX,100,MAX,10,60,0],]
'''
        
if __name__ == '__main__':
  pass
