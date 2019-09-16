#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here


    def router_main(self, net):
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''

        my_interfaces = self.net.interfaces();
        myIPs = {}
        for intf in my_interfaces:
            myIPs[str(intf.ipaddr)] = intf.ethaddr

        log_debug(myIPs)
        # initialize empty mapping table

        map = {}
        while True:
            gotpkt = True
            try:
                timestamp,dev,pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_debug("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_debug("Got shutdown signal")
                break

            if gotpkt:
                log_debug("Got a packet: {}".format(str(pkt)))

                if pkt.has_header(Arp):

                    arp = pkt.get_header(Arp)

                    log_debug("Got an arp request {}".format(str(arp)))

                    #if the destination IP is assigned to us, send ARP reply
                    if str(arp.targetprotoaddr) in myIPs:
                        log_debug("destination matches one of my IPs")
                        # we are now sending a reply
                        replyPkt = create_ip_arp_reply(myIPs[str(arp.targetprotoaddr)], arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)
                        log_debug("sending arp reply {}".format(str(replyPkt)))

                        net.send_packet(dev, replyPkt)

                    #if packet is reply and its dest IP in assigned to us
                    elif arp.operation is ArpOperation.Reply and str(arp.targetprotoaddr) in myIPs:
                        log_debug("arp reply seen and destination matches one of my IPs")
                        map[str(arp.senderprotoaddr)] = arp.senderhwaddr




def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main(net)
    net.shutdown()
