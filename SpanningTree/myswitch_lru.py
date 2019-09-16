'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *
from lru import *

def main(net):
    my_interfaces = net.interfaces()  # gets a list of interfaces on this router
    mymacs = [intf.ethaddr for intf in my_interfaces] # gets the ethernet addresses for every interface
    cache = lruCache(5)

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        # src and dest are mac addresses
        # input_port appears to be the name of the port

        #add src and input port pair to cache
        newSrc = lruEntry(packet[0].src, input_port)

        cache.print()
        cache.push(newSrc)

        log_debug("In {} received packet {} on {}".format(net.name, packet, input_port))
        if packet[0].dst in mymacs:
            log_debug("Packet intended for me")

        elif cache.contains(packet[0].dst):
            log_debug("Packet destination in LRU cache")
            dstPort = cache.getPort(packet[0].dst)
            for intf in my_interfaces:
                if dstPort == intf.name:
                    log_debug("Sending packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)

        else: # broadcast
            for intf in my_interfaces:
                if input_port != intf.name:
                    log_debug("Flooding packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)
    net.shutdown()
