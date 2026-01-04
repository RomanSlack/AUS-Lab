# agentic/raft_service.py

from pysyncobj import SyncObj, replicated

class RaftService(SyncObj):
    def __init__(self, self_address, partner_addrs):
        super(RaftService, self).__init__(self_address, partner_addrs)
        self.leader = None
        self.state = {}

    @replicated
    def set_value(self, key, value):
        self.state[key] = value

    def get_value(self, key):
        return self.state.get(key)

    def get_leader(self):
        return self.leader

    def is_leader(self):
        return self._isLeader()
