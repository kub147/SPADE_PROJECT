# project/agents/resource_agent.py
# (MODIFIED - LIMITED BANDWIDTH)

import asyncio
import json
import time
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

# Definitions
PROTOCOL_RESOURCE_REQUEST = "ResourceProtocol"
MONITOR_AGENT_JID = "monitor@localhost"

class ResourceAgent(Agent):
    """
    Manages educational materials.
    *** NEW: Simulates limited bandwidth. ***
    """

    async def setup(self):
        # --- Knowledge Base (Simple resource database) ---
        self.resources = {
            "mathematics": "https://www.math-videos.com/algebra-basics",
            "physics": "https://www.physics-explained.com/newtons-laws",
            "history": "https://www.history-channel.com/ww2-overview",
            "biology": "https://www.biology-world.com/cells"
        }
        
        # --- NEW: Bandwidth Management ---
        self.max_bandwidth = 2  # Can only serve 2 students at a time
        self.current_load = 0   # How many students are currently downloading

        print(f"{self.name}: Ready. Max bandwidth: {self.max_bandwidth}.")

        template = Template()
        template.set_metadata("protocol", PROTOCOL_RESOURCE_REQUEST)
        template.set_metadata("performative", "request")

        self.add_behaviour(self.ResourceResponderBehav(), template)

    def get_resource_for_topic(self, topic):
        return self.resources.get(topic.lower().strip())

    class ResourceResponderBehav(CyclicBehaviour):
        async def run(self):
            print(f"{self.agent.name}: Waiting... (Load: {self.agent.current_load}/{self.agent.max_bandwidth})")
            msg = await self.receive(timeout=1000)

            if msg:
                topic_requested = msg.body
                print(f"{self.agent.name}: Received request for '{topic_requested}' from {str(msg.sender)}")

                # 1. Check bandwidth
                if self.agent.current_load >= self.agent.max_bandwidth:
                    # --- Server is busy ---
                    print(f"{self.agent.name}: Server busy. Rejecting request.")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", "failure") # Use 'failure'
                    reply.body = "ERROR_SERVER_BUSY"
                    await self.send(reply)
                    return # Stop processing this message

                # 2. Get resource (if not busy)
                self.agent.current_load += 1 # Occupy a slot
                resource_link = self.agent.get_resource_for_topic(topic_requested)
                reply = msg.make_reply()
                reply.set_metadata("performative", "inform")

                if resource_link:
                    # --- Simulate download time ---
                    print(f"{self.agent.name}: Serving resource... (Load: {self.agent.current_load}/{self.agent.max_bandwidth})")
                    await asyncio.sleep(random.randint(5, 10)) # Download takes 5-10s
                    
                    reply.body = resource_link
                    
                    # --- Report to monitor ---
                    monitor_msg = Message(to=MONITOR_AGENT_JID)
                    monitor_msg.set_metadata("protocol", "MonitorProtocol")
                    monitor_msg.set_metadata("performative", "inform")
                    monitor_msg.body = json.dumps({
                        "event": "RESOURCE_PROVIDED", "student": str(msg.sender),
                        "topic": topic_requested, "resource": resource_link,
                        "timestamp": time.time()
                    })
                    await self.send(monitor_msg)
                else:
                    reply.body = "ERROR_NOT_FOUND"

                # 3. Send reply and free up slot
                await self.send(reply)
                print(f"{self.agent.name}: Sent reply: {reply.body}")
                self.agent.current_load -= 1 # Free up the slot