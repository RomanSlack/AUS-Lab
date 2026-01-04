# agentic/state_manager.py

import json
import threading
import time

class StateManager:
    def __init__(self, redis_client, api_client, node_id):
        self.redis = redis_client
        self.api_client = api_client
        self.node_id = node_id
        self.state_publisher_thread = threading.Thread(target=self._publish_state)
        self.state_publisher_thread.daemon = True
        self.state_subscriber_thread = threading.Thread(target=self._subscribe_to_state)
        self.state_subscriber_thread.daemon = True

    def start(self):
        self.state_publisher_thread.start()
        self.state_subscriber_thread.start()

    def _publish_state(self):
        while True:
            try:
                state = self.api_client.get_state()
                if state:
                    self.redis.publish("state", json.dumps(state))
            except Exception as e:
                print(f"[{self.node_id}] Error publishing state: {e}")
            time.sleep(1)

    def _subscribe_to_state(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe("state")
        for message in pubsub.listen():
            if message['type'] == 'message':
                # In a real application, you would do something with the state received from other nodes
                # For now, we just print it
                # print(f"[{self.node_id}] Received state from another node: {message['data']}")
                pass
