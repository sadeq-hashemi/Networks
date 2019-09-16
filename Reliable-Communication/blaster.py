#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint, choice
from string import ascii_letters
from threading import Timer
from time import time
from math import floor

myEthAddr = '10:00:00:00:00:01'
myIP = '192.168.100.1'
middleboxIP = '192.168.100.1/30'
num = None
length = None
SW = None
TO = None
rcvTO = None
win = None  # type: sliding_window
last_sent = 0.0

class pktHeader():
    def __init__(self, seqNum, length):
        self.seqNum = seqNum
        self.length = length

class winObj:
    def __init__(self, seqNum, pkt, time, length):
        self.seqNum =  seqNum
        self.length = length
        self.pkt = pkt
        self.time = time
        self.reTX = 0
        self.ack = False


class sliding_window:
    def __init__(self, SW, TO):
        self.size = 0

        self.LHS = 0
        self.RHS = 0
        self.SW = SW
        self.TO = TO

        self.sentByte = 0
        self.sentByteTotal = 0
        self.numTO = 0

        self.startTime = None
        self.endTime = None

        self.list = []

    def checkSize(self):
        return (self.RHS + 1) - self.LHS <= self.SW

    def rcvAck(self, seqNum ):
        ind = self.LHS

        #find the seqNum that this ack corresponds to and acknowledge it
        while(ind < self.size):
            log_debug("checking in seqNum {} against {}".format(self.list[ind].seqNum, seqNum))
            if(self.list[ind].seqNum == seqNum):
                self.list[ind].ack = True
                log_debug("acknowledging....")
                break
            ind += 1


        #update LHS to new valid position
        while(self.LHS < self.size and self.list[self.LHS].ack):
            self.LHS += 1
            log_debug("LHS = {} size = {}".format(self.LHS, self.size))



    def addPkt(self, pktSeqNum, pkt, length):
        obj = winObj(pktSeqNum, pkt, floor(time()*1000), length)
        self.list.append(obj)
        self.size += 1
        self.sentByte += length
        self.sentByteTotal += length

    def getNext(self):
        if(self.RHS + 1) < self.size:
            sendPkt(self.list[self.RHS])
            self.RHS += 1

    # scans LHS and makes sure
    def update(self, currTime):
        ind = self.LHS

        # while(ind < self.LHS):
        #     sendPkt(self.list[ind].pkt) # TODO : fix for later

        if ind < self.size and currTime - self.list[ind].time > self.TO:
            log_debug("LHS has not been acknowledged for {} ms".format(currTime - self.list[ind].time))
            self.sentByteTotal += self.list[ind].length
            return self.list[ind].pkt

        log_debug("no retransmissions...")
        return None


def print_output(total_time, num_ret, num_tos, throughput, goodput):
    print("Total TX time (s): " + str(total_time))
    print("Number of reTX: " + str(num_ret))
    print("Number of coarse TOs: " + str(num_tos))
    print("Throughput (Bps): " + str(throughput))
    print("Goodput (Bps): " + str(goodput))


def mkPkt():
    global win

    pkt = Packet()
    pkt += Ethernet()
    pkt += IPv4()
    pkt += UDP()
    pkt[Ethernet].src = myEthAddr
    pkt[Ethernet].dst = "20:00:00:00:00:01"
    pkt[IPv4].src = myIP
    pkt[IPv4].dst = "192.168.200.1"
    pkt[UDP].src = 999
    pkt[UDP].dst = 999


    pkt[1].protocol = IPProtocol.UDP

    pktheader = pktHeader(win.size, randint(0, length))
    pktData = ''.join([choice(ascii_letters) for x in range(pktheader.length)])
    pkt += (pktheader.seqNum).to_bytes(4, 'little')
    pkt += (pktheader.length).to_bytes(2, 'little')
    pkt += bytes(pktData, 'utf8')

    win.addPkt(pktheader.seqNum, pkt, pktheader.length)

    return pkt

def canSend():
    global  last_sent
    if math.floor(time.time()*1000) - last_sent >= rcvTO:
        return True
    return False

def sendPkt(net, blastee, pkt):
    global last_sent
    try:
        net.send_packet(blastee.name, pkt)
    except Exception as e:
        log_failure("Can't send packet: {}".format(str(e)))
    #last_sent = math.floor(time.time()*1000)


def readParams():
    path = './blaster_params.txt'
    with open(path) as f:
        lines = f.readlines()
        for l in lines:
            args = l.split()
            if args is not None and len(args) % 2 == 0:
                for i in range(0, len(args), 2):
                    if(args[i] == '-n'):
                         num = args[i+1]
                    elif(args[i] == '-l'):
                        length = args[i+1]
                    elif(args[i] == '-w'):
                        SW = args[i+1]
                    elif(args[i] == '-t'):
                        TO = args[i+1]
                    elif(args[i] == '-r'):
                        rcvTO = args[i+1]
    return  int(num, 10), int(length, 10), int(SW, 10), float(TO), rcvTO

def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]
    print("here")
    blastee = my_intf[0]
    for f in my_intf:
        log_debug("f = {}".format(f))
        if f.ipaddr == middleboxIP:
            blastee = f
            log_debug("matched = {}".format(f))

    global num
    global length
    global SW
    global TO
    global rcvTO
    global win
    num, length, SW, TO, rcvTO = readParams()
    rcvTO = float(rcvTO)/1000.0
    log_debug("Read parameters num:{} len:{} SW:{} TO:{} rcvTO:{}".format(num, length, SW, TO, rcvTO, win))

    win = sliding_window(SW, TO)
    log_debug("win created: {}".format(win))

    n = 0
    while True:
        gotpkt = True
        try:
            #Timeout value will be parameterized!
            timestamp,dev,pkt = net.recv_packet(timeout=rcvTO)

        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet")
            dstIP = pkt.get_header(IPv4).dst

            #if dstIP == myIP:
            log_debug("packet is destined for blaster IP address")

            # seqNum = pkt.get_header(pktHeader).seqNum  # make sure this works
            data = pkt[3].to_bytes()
            log_debug("data: {}".format(data))
            seqNum = int.from_bytes(data[:4], "little")
            log_debug("seqNum is {}, entering acknowledge".format(seqNum))
            win.rcvAck(seqNum)


        else:
            log_debug("Didn't receive anything")

            '''
            Creating the headers for the packet
            '''
            if n < num and win.checkSize():
                log_debug("creating packet")
                pkt = mkPkt()
                log_debug("created pkt {}".format(pkt))
                log_debug("sending pkt {} to blastee".format(n+1))

                sendPkt(net, blastee, pkt)
                n += 1

                # try:
                #     net.send_packet(blastee.name, pkt)
                #     n += 1
                # except Exception as e:
                #     log_failure("Can't send packet: {}".format(str(e)))

            '''
            Do other things here and send packet
            '''
        retx = win.update(floor(time()*1000)) # MAKE SURE THAT WE CAN SEND TWICE PER LOOP
        if retx is not None:
            sendPkt(net, blastee, retx)


    net.shutdown()
