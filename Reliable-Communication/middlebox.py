#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import random
import time

params_file = "middlebox_params.txt"

def readParams():
    path = './middlebox_params.txt'
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            args = l.split()
            if(len(args) % 2 == 0):
                for i in range(0, len(args), 2):
                    if(args[i] == '-s'):
                        seed = args[i+1]
                    elif(args[i] == '-p'):
                        prob_drop = args[i+1]
    return  int(seed, 10), int(prob_drop, 10)

def drop(percent):
    return random.randrange(100) < percent

def switchy_main(net):

    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]
    random_seed, prob_drop = readParams()

    random.seed(random_seed) #Extract random seed from params file


    while True:
        gotpkt = True
        try:
            timestamp, dev, pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet {}".format(pkt))

        if dev == "middlebox-eth0":
            log_debug("Received from blaster")
            '''
            Received data packet
            Should I drop it?
            '''
            if not drop(prob_drop):
                log_debug("forwarded to blastee")
                net.send_packet("middlebox-eth1", pkt)
            else:
                log_debug("dropped")

            '''
            If not, modify headers & send to blastee
            '''

        elif dev == "middlebox-eth1":
            log_debug("Received from blastee")
            net.send_packet("middlebox-eth0", pkt)
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!
            
            '''
        else:
            log_debug("Oops :))")

    net.shutdown()
