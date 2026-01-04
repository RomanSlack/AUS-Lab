# agentic/replication_service.py

class ReplicationService:
    def __init__(self, redis_client):
        self.redis = redis_client

    def publish_command(self, command):
        self.redis.publish("commands", command)
