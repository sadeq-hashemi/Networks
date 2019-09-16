class Root(object):
    def __init__(self, rootID, rootMAC, hops, srcPort):
        self._rootID = rootID
        self._rootMAC = rootMAC
        self._hops = hops
        self._srcPort = srcPort

    @property
    def rootID(self):
        return self._rootID

    @rootID.setter
    def rootID(self, value):
        self._rootID = int(value)

    @property
    def rootMAC(self):
        return self._rootMAC

    @rootMAC.setter
    def rootMAC(self, rootMAC):
        self._rootMAC = rootMAC

    @property
    def hops(self):
        return self._hops

    @hops.setter
    def hops(self, value):
        self._hops = value

    @property
    def srcPort(self):
        return self._srcPort

    @srcPort.setter
    def srcPort(self, port):
        self._srcPort = port
