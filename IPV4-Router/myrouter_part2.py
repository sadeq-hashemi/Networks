#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time

from switchyard.lib.packet.util import *
from switchyard.lib.userlib import *

class pktEntry(object):
    def __init__(self, pkt, route, srcName):
        self.pkt = pkt
        self.route = route
        self.srcName = srcName
        self.time = time.time()
        self.arpReq = 0 # number of times we have sent an arp request


class tableEntry(object):

    def __init__(self, prefix, mask, hop, name):
        self.prefix = prefix
        self.mask = mask
        self.hop = hop
        self.name = name


class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here

    def __get_intf(self, my_interfaces, name):
        log_debug("Searching for interface {} in my interfaces".format(name))
        for intf in my_interfaces:
            if name == intf.name:
                return intf

        log_debug("While searching for interfaces found nothing")
        return None
    def init_forwardtable(self, my_interfaces):
        t = []

        for intf in my_interfaces:
            t.append(tableEntry(IPv4Address(int(intf.ipaddr) & int(intf.netmask)), intf.netmask, intf.ipaddr, intf.name))

        log_debug("Initializing forward table...")
        file = open('forwarding_table.txt', 'r')

        for line in file:
            x = line.split(' ')
            prefix = IPv4Address(x[0])
            mask = IPv4Address(x[1])
            hop = IPv4Address(x[2])
            name = x[3].strip('\n')
            t.append(tableEntry(prefix, mask, hop, name))
        return t

    def __get_route(self, forwardtable, dst):

        rt = None
        name = None
        max_prefixnet = None
        for entry in forwardtable:
            prefixnet = IPv4Network(str(entry.prefix) + "/" + str(entry.mask))

            if dst in prefixnet: #found a match
                if max_prefixnet is None or prefixnet.prefixlen > max_prefixnet.prefixlen:
                    rt = entry.hop
                    name = entry.name
                    max_prefixnet = prefixnet

        log_debug("Searched for a route for dst = {}, route = {} on interface {} ".format(dst, rt, name))
        return rt, name

    def __create_arp_request(self, src_ip, src_ether, target_ip):

        log_debug("arp request for src ip = {}, src ether = {}, and dst ip = {} ".format(src_ip, src_ether, target_ip))
        arp = Arp(operation=ArpOperation.Request,
                  senderhwaddr=src_ether,
                  senderprotoaddr=src_ip,
                  targethwaddr='ff:ff:ff:ff:ff:ff',
                  targetprotoaddr=target_ip)
        return arp

    def __arp_query(self, my_interfaces, src, arp_pkt, donotsendIP):
        # for intf in my_interfaces:
        #     if intf.ipaddr is not donotsendIP:
        #         ether = Ethernet()
        #         ether.src = src_ether
        #         ether.ethertype = EtherType.ARP
        #         ether.dst = 'ff:ff:ff:ff:ff:ff'
        #         arppacket = ether + arp_pkt
        #         self.net.send_packet(intf.name, arppacket)

        ether = Ethernet()
        ether.src = src.ethaddr
        ether.ethertype = EtherType.ARP
        ether.dst = 'ff:ff:ff:ff:ff:ff'
        arppacket = ether + arp_pkt
        log_debug("Arp query : {} on {}".format(arppacket, src.name))

        self.net.send_packet(src.name, arppacket)

    def router_main(self, net):
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''

        my_interfaces = self.net.interfaces()
        my_IP_Eth = {}
        for intf in my_interfaces:
            log_debug("{}".format(intf.ipaddr))
            my_IP_Eth[str(intf.ipaddr)] = intf.ethaddr
        # initialize empty mapping table
        arp_map = {}
        #arp_map = {key: value for key, value in my_IP_Eth.items()}

        # packet set that are stashed until their arp arrives
        pkt_list = []

        forwardtable = self.init_forwardtable(my_interfaces)
        log_debug("forward table created")

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

                    #if packet is reply and its dest IP in assigned to us
                    if arp.operation is ArpOperation.Reply and str(arp.targetprotoaddr) in my_IP_Eth:
                        log_debug("arp reply seen and destination matches one of my IPs, adding {} : {}".format(str(arp.senderprotoaddr),  str(arp.senderhwaddr)))
                        arp_map[str(arp.senderprotoaddr)] = {"ethaddr": arp.senderhwaddr, "lastUsed": time.time(), "numSent": 0}

                    #if the destination IP is assigned to us, send ARP reply
                    elif str(arp.targetprotoaddr) in my_IP_Eth:
                        log_debug("destination matches one of my IPs")
                        # we are now sending a reply
                        replyPkt = create_ip_arp_reply(my_IP_Eth[str(arp.targetprotoaddr)], arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)
                        log_debug("sending arp reply {}".format(str(replyPkt)))

                        net.send_packet(dev, replyPkt)


                if pkt.has_header(IPv4):

                    ipv4 = pkt.get_header(IPv4)
                    ipv4.ttl -= 1  # decrememnt TTL

                    #find route with longest destination match
                    route, srcName = self.__get_route(forwardtable, ipv4.dst)
                    if route is not None and str(ipv4.dst) not in my_IP_Eth: # found a route
                        log_debug("Route was found and the dst is not one of our interfaces")
                        src = self.__get_intf(my_interfaces, srcName)  # sender

                        # if we have the eth address in arp map, update the time
                        if str(route) in arp_map:
                            log_debug("Route exists in arp map")
                            if not pkt.has_header(Ethernet):
                                pkt = Ethernet() + pkt
                            pkt[Ethernet].src = src.ethaddr  # use the interface in f table
                            pkt[Ethernet].dst = arp_map[str(route)]  # find the eth addr of next hop ip
                            self.net.send_packet(srcName, pkt)
                        # else send an arp request for the ip, and stash the pkt for the future
                        else :
                            # send arp query
                            log_debug("Route did not exist, sending arp query")

                            arpPkt = self.__create_arp_request(src.ipaddr, src.ethaddr, ipv4.dst)
                            self.__arp_query(my_interfaces, src, arpPkt, ipv4.src)
                            pkt_list.append(pktEntry(pkt, route, srcName))


                # loop through unsent packets and send if possible
                log_debug("Iterating through old packets")
                newList = []
                log_debug("arp table {}".format(arp_map))
                for entry in pkt_list:
                    srctemp = self.__get_intf(my_interfaces, entry.srcName)  # sender
                    log_debug("searching for {} ".format(entry.route))
                    log_debug("Old packet :  {}".format(entry.pkt.get_header(IPv4)))
                    sent = False
                    if str(entry.pkt.get_header(IPv4).dst) in arp_map:  # eth addr is available, send pkt, and discard
                        log_debug("Found route for an old packet")
                        if not entry.pkt.has_header(Ethernet):
                            entry.pkt = Ethernet() + entry.pkt

                        entry.pkt[Ethernet].src = srctemp.ethaddr  # use the interface in f table

                        entry.pkt[Ethernet].dst = arp_map[str(entry.pkt.get_header(IPv4).dst)]['ethaddr'] # find the eth addr of next hop ip
                        self.net.send_packet(entry.srcName, entry.pkt)
                        sent = True

                    elif(int(time.time() - entry.time) >= 1): # if no reply within 1 second and
                        log_debug("A second has passed for packet {}".format(entry.pkt.get_header(IPv4)))
                        entry.arqReq += 1
                        if(entry.arqReq < 3): # if we have not queried thrice, query, and add to new list
                            log_debug("Try number {} for packet {}".format(entry.arpReq, str(entry.pkt.get_header(IPv4))))

                            arpPkt = self.__create_arp_request(srctemp.ipaddr, srctemp.ethaddr, entry.route.hop)
                            self.__arp_query(my_interfaces, srctemp, arpPkt, pkt.get_header(IPv4).src)
                            #pkt_list.srcadd(pktEntry(pkt, route))


                    if not sent and entry.arpReq < 3:
                        newList.append(entry)

                pkt_list = newList



                    











def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main(net)
    net.shutdown()
