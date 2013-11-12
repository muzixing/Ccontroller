#!/usr/bin/python
"""
	This is a topu of our test. It shows that how to add an interface(for example a real hardware interface) to a network after the network is created.
    This code writed by li cheng, after learning mininet of sprient's.
"""
import re

from mininet.cli import CLI
from mininet.log import setLogLevel, info,error
from mininet.net import Mininet
from mininet.topolib import TreeTopo
from mininet.util import quietRun

def checkIntf(intf):
	#make sure intface exists and is not configured.
	if(' %s:'% intf) not in quietRun('ip link show'):
		error('Error:', intf, 'does not exist!\n' )
		exit(1)
	ips = re.findall( r'\d+\.\d+\.\d+\.\d+', quietRun( 'ifconfig ' + intf ) )
	if ips:
		error("Error:", intf, 'has an IP address,'
			'and is probably in use!\n')
			exit(1)
if __name__ == "__main__":
	setLogLevel("info")
	newIntf = 'eth1'
	OVSKernelSwitch.setup()
	intfName_1 = "eth2"
	intfName_3 = "eth3"
	info("********checking", intfName_1, '\n')
	checkIntf(intfName_1)
	info("********checking", intfName_2, '\n')
	checkIntf(intfName_2)

	info("*******creating network\n")
	net = Mininet(listenPort = 6633)

	mycontroller = RemoteController("muziController", ip = "192.168.0.1")

	switch_1 = net.addSwitch('s1')
	switch_2 = net.addSwitch('s2')
	switch_3 = net.addSwitch('s3')
	switch_4 = net.addSwitch('s4')

	net.controller = [mycontroller]
	info("*****Adding hardware interface ", intfName_1, "to switch:" switch_1.name, '\n')
	info("*****Adding hardware interface ", intfName_3, "to switch:" switch_3.name, '\n')

	_intf_1 = Intf(intfName_1, node = switch_1)
	_intf_3 = Intf(intfName_3, node = switch_3)

	net.addLink(switch_1, switch_2, '2', '1')
	net.addLink(switch_2, switch_3, '2', '3')
	net.addLink(switch_1, switch_4, '3', '1')
	net.addLink(switch_4, switch_3, '2', '2')

	net.start()
	CLI(net)
	net.stop()



