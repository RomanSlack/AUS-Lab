# agentic/redis_service.py

import redis

class RedisService:
    def __init__(self, host='localhost', port=6379, db=0):
        self.redis = redis.Redis(host=host, port=port, db=db)

    def publish(self, channel, message):
        self.redis.publish(channel, message)

    def subscribe(self, channel):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel)
        return pubsub