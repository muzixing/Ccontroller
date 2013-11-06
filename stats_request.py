import libopencflow as of

#we need to send the stats request packets periodically
msg = []

msg[0] = of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 0)            										#Type of  OFPST_DESC (0)       
msg[1] = of.ofp_header(type = 16, length = 56)/of.ofp_stats_request(type =1)\
                                       	/of.ofp_flow_wildcards()\
                                        /of.ofp_match()\
                                        /of.ofp_flow_stats_request()															#flow stats
msg[2]= of.ofp_header(type = 16, length =56)/of.ofp_stats_request(type = 2)\
                                         /of.ofp_flow_wildcards()/of.ofp_match()\
                                        /of.ofp_aggregate_stats_request()                                  						# aggregate stats request
msg[3] = of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 3)             										#Type of  OFPST_TABLE (0) 
msg[4] = of.ofp_header(type = 16, length =20)/of.ofp_stats_request(type = 4)/of.ofp_port_stats_request(port_no = 1)				# port stats request       

msg[5] = of.ofp_header(type = 16, length =20)/of.ofp_stats_request(type =5)/of.ofp_queue_stats_request()
msg[6]= of.ofp_header(type = 16, length = 12)/of.ofp_stats_request(type = 0xffff)  #vendor request


def send(self, type):
	self.type = Type
	return msg[Type]
	
	