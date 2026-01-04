# agentic/gossip_service.py

import asyncio
import gossipy

class GossipService:
    def __init__(self, host, port, seeds):
        self.node = gossipy.Gossip(host=host, port=port, seeds=seeds)

    async def start(self):
        await self.node.start()

    async def get_members(self):
        return self.node.get_members()

    async def broadcast(self, message):
        await self.node.broadcast(message)
