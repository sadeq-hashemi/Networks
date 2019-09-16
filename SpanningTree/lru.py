class lruEntry(object):
    def __init__(self, src, port=None):
        self.src = src
        self.port = port

    def __eq__(self, other):
        return self.src == other.src

    def getPort(self):
        return self.port

    def getSrc(self):
        return self.src


class lruCache(object):

    def __init__(self, size = 5):
        self.maxSize = size
        self.size = 0
        self.cache = [] # end of list (rightmost) is head, start is index 0

    def push(self, entry):
        if entry in self.cache:
            self.cache.remove(entry)
            self.size -= 1

        if self.size >= self.maxSize:
            self.cache.pop(0)
            self.size -= 1

        self.cache.append(entry)
        self.size += 1

    def pop(self):
        if self.size > 0:
            self.cache.pop(0)
            self.size -= 1

    def contains(self, dst):
        entry = lruEntry(dst, None)  # dummy entry to search for source

        if entry in self.cache:
            return True

        return False


    # looks if dst in the cache we remove it and push it back
    def getPort(self, dst):

        entry = lruEntry(dst, None)  # dummy entry to find dst
        ret = next((cacheEntry.getPort() for cacheEntry in self.cache if cacheEntry == entry), None)  # if dst exists in cache, return its port

        if ret is not None:
            entry = lruEntry(dst, ret) # recreate true entry
            self.push(entry) # push it back

        return ret

    def print(self):
        for entry in self.cache:
            print("src: " + str(entry.src) + " port: " + str(entry.port))

        print()
