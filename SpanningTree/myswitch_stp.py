'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
from switchyard.lib.userlib import *

from spanningtreemessage import *
from Root import *
from lru import *
import threading

end = False


def ethToId(mac) :
    return int((str(mac)).replace(":", ""), 16)

def findMyId(my_interfaces):
    minId = None
    minMAC = None
    minName = None
    for intf in my_interfaces:
        id = ethToId(intf.ethaddr)
        if minId is None or id < minId :
            minId = id
            minMAC = intf.ethaddr
            minName = intf.name

        #log_debug("id hex = {}".format(ids))
        #ids_array.append(int(ids, 16))
        #log_debug("id dec = {}".format(ids_array[i]))

    return minId, minMAC, minName

def sendSTP(root, myMAC, my_interfaces, net, exempt = None) :
    spm = SpanningTreeMessage(root.rootMAC,  hops_to_root=root.hops)
    Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
    pkt = Ethernet(src= myMAC,
                    dst="ff:ff:ff:ff:ff:ff",
                    ethertype=EtherType.SLOW) + spm
    xbytes = pkt.to_bytes()
    p = Packet(raw=xbytes)


    # send packet info to all
    for intf in my_interfaces:
        if exempt is None or exempt != intf.name:
            log_debug("Flooding spanning tree message packet {} to {}".format(p, intf.name))
            net.send_packet(intf.name, p)




def emitSTP(root, myMAC, myID, my_interfaces, net):

    if root.rootID == myID and not net.scenario.done():
        spm = SpanningTreeMessage(root.rootMAC, hops_to_root=root.hops)
        Ethernet.add_next_header_class(EtherType.SLOW, SpanningTreeMessage)
        pkt = Ethernet(src=myMAC,
               dst="ff:ff:ff:ff:ff:ff",
               ethertype=EtherType.SLOW) + spm
        xbytes = pkt.to_bytes()
        p = Packet(raw=xbytes)

        # send packet info to all
        for intf in my_interfaces:
            log_debug("Flooding spanning tree message packet {} to {}".format(p, intf.name))
            net.send_packet(intf.name, p)

        threading.Timer(2.0, emitSTP, [root, myMAC, myID, my_interfaces, net]).start()



def main(net):
    my_interfaces = net.interfaces()  # gets a list of interfaces on this router
    mymacs = [intf.ethaddr for intf in my_interfaces] # gets the ethernet addresses for every interface
    cache = lruCache(5)


    myId, myMAC, myName = findMyId(my_interfaces)

    root = Root(myId, myMAC, 0, myName)
    log_debug("My ID = {} root {}".format(myId, root.rootMAC))

    #sendSTP(root, my_interfaces, net) # flood to nodes
    emitSTP(root, myMAC, myId, my_interfaces, net)

    forwardTable = {}
    # dictionary of interface:forward
    for intf in my_interfaces:
        forwardTable[intf.name] = True


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

        if packet.has_header(SpanningTreeMessage): #STP packet
            msg = SpanningTreeMessage()

            msg.from_bytes(packet[1].to_bytes())
            log_debug("Spanning Tree Message found with root {} {}, current root is {} {} on {}".format(msg.root,
                                                                                                  msg.hops_to_root,
                                                                                                  root.rootMAC,
                                                                                                  root.hops, root.srcPort))

            # log_debug("||||||||||||||||||| msg {}  root {}".format(msg.root), root.rootMAC())

            if ethToId(msg.root) < root.rootID:
                log_debug("Spanning Tree Message root was less than current root")

                root = Root(ethToId(msg.root),
                            msg.root,
                            msg.hops_to_root + 1,
                            input_port)

                forwardTable[input_port] = True
                sendSTP(root, myMAC, my_interfaces, net, input_port)
            elif ethToId(msg.root) == root.rootID and msg.hops_to_root + 1 < root.hops:
                log_debug("Spanning Tree Message root was same as current but shorter distance found")

                forwardTable[input_port] = True
                root.hops = msg.hops_to_root + 1
                root.srcPort = input_port
                sendSTP(root, myMAC, my_interfaces, net, input_port)
            elif input_port != root.srcPort and msg.hops_to_root + 1 == root.hops:
                log_debug("Spanning Tree Message different roots but same distance, blocking {}".format(input_port))
                forwardTable[input_port] = False



        elif packet[0].dst in mymacs:
            log_debug("Packet intended for me")

        elif cache.contains(packet[0].dst):
            log_debug("Packet destination in LRU cache")
            dstPort = cache.getPort(packet[0].dst)
            for intf in my_interfaces:
                if dstPort == intf.name:
                    log_debug("Sending packet {} to {}".format(packet, intf.name))
            #log_debug("Packet destination in LRU cache")
            dstPort = cache.getPort(packet[0].dst)
            for intf in my_interfaces:
                if dstPort == intf.name:
                    #log_debug("Sending packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)

        else: # broadcast
            for intf in my_interfaces:
                log_debug(intf.name + " " + str(forwardTable[intf.name]))
                if input_port != intf.name and forwardTable[intf.name]:
                    log_debug("Flooding packet {} to {}".format(packet, intf.name))
                    net.send_packet(intf.name, packet)

    net.shutdown()
