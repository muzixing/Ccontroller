from scapy.all import *
#import libopencflow as ofc
#_______________________________________you can set the switch and port information here_______________


sw_type = ["010","111","000","101","100"]
f = ["0010000010","1111111111","0000000000","1100101000","1010101010"]
wave = ["101","100","000","111","001"]


#____________________________________________________________________________________________________
class  MyPort():
	def __init__(self, f, wave, port_no):
		self.f = f
		self.wave =wave
		self.port_no = port_no
#______________port_info________________________
		self.OFPST_FIBER = f[port_no][0]     # 1<<15 can switch circuits based on SM/MM fiber
		self.OFPST_WAVE = f[port_no][1]      # 1<<14 can switch circuits based on ITU-T lambdas
		self.OFPST_T_OTN = f[port_no][2]     # 1<<13 can switch circuits based on OTN standard
		self.OFPST_T_SDH = f[port_no][3]     # 1<<12 can switch circuits based on SDH standard
		self.OFPST_T_SONET = f[port_no][4]   # 1<<11 can switch circuits based on SONET standard
		self.OFPST_ETH = f[port_no][5]       # 1<<4 can switch packets based on ETH headers
		self.OFPST_VLAN = f[port_no][6]      # 1<<3 can switch packets based on VLAN tags
		self.OFPST_MPLS = f[port_no][7]      # 1<<2 can switch packets based on MPLS labels
		self.OFPST_IP = f[port_no][8]        # 1<<1 can switch packets based on IP headers 
		self.OFPST_L4 = f[port_no][9]        # 1<<0 can switch packets based on TCP/UDP headers

#________________wave sw________________________
		self.center_freq_lmda = wave[port_no][0]
		self.num_lmda = wave[port_no][1]
		self.freq_space_lmda = wave[port_no][2]
	
class  sw():
	def __init__(self,sw_type, sw_no):
		self.sw_type = sw_type
		self.sw_no = sw_no

		self.type_ip = sw_type[sw_no][0]
		self.type_otn = sw_type[sw_no][1]
		self.type_wave = sw_type[sw_no][2]


#______________________________________________________________________________________________________
#we creat switch by using the function below.
def creat_port(port_no):
	new_port = MyPort(f, wave, port_no)
	return new_port
def creat_sw(sw_no):
	return sw(sw_type, sw_no)
#______________________________________________________________________________________________________

if __name__ == '__main__':
	pass
