from scapy.all import *

#____________________________________________________________________________________________________
class  sw(self, sw_type[3], f[11], w[3]):
	"""you can set what your want."""
	self.type_ip=sw_type[0],
	self.type_otn=sw_type[1],
	self.type_wave=sw_type[2],

	def port_setting():
		OFPST_FIBER = f[0],   # 1<<15 can switch circuits based on SM/MM fiber
		OFPST_WAVE = f[1],     # 1<<14 can switch circuits based on ITU-T lambdas
       	OFPST_T_OTN = f[2],    # 1<<13 can switch circuits based on OTN standard
        OFPST_T_SDH = f[3],  # 1<<12 can switch circuits based on SDH standard
        OFPST_T_SONET = f[4],  # 1<<11 can switch circuits based on SONET standard
        NOT_DEFINED = f[5],  # Not used
        OFPST_ETH = f[6],  # 1<<4 can switch packets based on ETH headers
        OFPST_VLAN = f[7],  # 1<<3 can switch packets based on VLAN tags
        OFPST_MPLS = f[8],  # 1<<2 can switch packets based on MPLS labels
        OFPST_IP = f[9],  # 1<<1 can switch packets based on IP headers 
        OFPST_L4 = f[10],  # 1<<0 can switch packets based on TCP/UDP headers

    def wave_port_setting():
    	center_freq_lmda = w[0],
        num_lmda = w[1],
        freq_space_lmda = w[2]

#______________________________________________________________________________________________________
def creat_sw():
	sw = sw(switch_type,field,wave)
	sw.port_setting()
	sw.wave_port_setting()
	return sw

#_______________________________________you can set the switch and port information here_______________
switch_type[3] = "010"
field[11] = "00100000010"
wave[3] = 100, 1, 50

#______________________________________________________________________________________________________
if __name__ == '__main__':
	pass
