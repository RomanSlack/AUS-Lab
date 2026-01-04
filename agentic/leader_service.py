# agentic/leader_service.py

import time
import threading

class LeaderService:
    def __init__(self, redis_client, node_id):
        self.redis = redis_client
        self.node_id = node_id
        self.leader = None
        self.leader_election_thread = threading.Thread(target=self._leader_election)
        self.leader_election_thread.daemon = True

    def start(self):
        self.leader_election_thread.start()

    def _leader_election(self):
        while True:
            try:
                # Try to acquire the leader lock
                if self.redis.set("leader", self.node_id, nx=True, ex=10):
                    self.leader = self.node_id
                    print(f"[{self.node_id}] I am the leader")
                else:
                    self.leader = self.redis.get("leader")
            except Exception as e:
                print(f"[{self.node_id}] Redis connection error during leader election. Retrying... {e}")
            time.sleep(5)

    def is_leader(self):
        return self.leader == self.node_id

    def get_leader(self):
        return self.leader
