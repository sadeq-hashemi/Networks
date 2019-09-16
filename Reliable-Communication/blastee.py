#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time

my_ip = '192.168.200.2'
my_ip_mask = '192.168.100.0/24'
my_mac = '20:00:00:00:00:01'

def create_ethernet_header(received_header):
    eth_hdr = Ethernet()
    eth_hdr.src = my_mac
    eth_hdr.dst = received_header.src
    eth_hdr.ethertype = received_header.ethertype
    return eth_hdr

def create_ipv4_header(received_header):
    ip_hdr = IPv4()
    ip_hdr.dst = received_header.src
    ip_hdr.src = my_ip
    return ip_hdr
#
# def ack_pay_load(whole_data_size, data_in_bytes):

def switchy_main(net):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    while True:
        gotpkt = True
        try:
            timestamp,dev,pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))
            # get the packet headers
            ethernet_header = pkt[Ethernet]
            #pkt.remove(Ethernet)
            ipv4_header = pkt[IPv4]
            #pkt.remove(IPv4)
            udp_header = pkt[UDP]
            #pkt.remove(UDP)

            log_debug("about to get sequnce number but not yet")
            # get sequence number
            # seq_num = pkt.getHeader.seqNum
            # pkt.remove(pkt.getHeader.seqNum)
            # pkt.remove(pkt.getHeader.len)
            data = pkt[3].to_bytes()
            log_debug("data: {}".format(data))
            seqNum = int.from_bytes(data[:4], "little")
            log_debug("seq num {}".format(seqNum))
            len = int.from_bytes(data[4:6], "little")
            log_debug("len num {}".format(len))
            # get pay load data

            pay_load = b'\x00\x00\x00\x00\x00\x00\x00\x00'
            if len < 8:
                pay_load =  data[6:len] + pay_load[len:8]
            else:
                pay_load = data[6:14]

            log_debug("payload is {}".format(pay_load))
            return_pkt = ethernet_header + ipv4_header + udp_header + data[:4] + pay_load
            net.send_packet(dev, return_pkt)


    net.shutdown()
