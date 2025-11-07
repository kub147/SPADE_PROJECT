# project/agents/resource_agent.py
# (FIXED VERSION)

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

# Definitions (must be the same as in other files)
PROTOCOL_RESOURCE_REQUEST = "ResourceProtocol"


class ResourceAgent(Agent):
    """
    ResourceAgent
    - Manages educational materials.
    - Responds to student requests by recommending materials.
    """

    async def setup(self):
        # --- Knowledge Base (Simple resource database) ---
        self.resources = {
            "mathematics": "https://www.math-videos.com/algebra-basics",
            "physics": "https://www.physics-explained.com/newtons-laws",
            "history": "https://www.history-channel.com/ww2-overview"
        }
        print(f"{self.name}: Ready. Managing {len(self.resources)} resources.")

        # --- Template for messages we react to ---
        template = Template()
        template.set_metadata("protocol", PROTOCOL_RESOURCE_REQUEST)
        template.set_metadata("performative", "request")

        self.add_behaviour(self.ResourceResponderBehav(), template)

    def get_resource_for_topic(self, topic):
        """
        Looks up a resource in the knowledge base.
        """
        return self.resources.get(topic.lower().strip())

    class ResourceResponderBehav(CyclicBehaviour):
        """
        This behaviour runs every time a message matching
        the setup() template is received.
        """

        async def run(self):
            print(f"{self.agent.name}: Waiting for a resource request...")

            msg = await self.receive(timeout=1000)

            if msg:
                topic_requested = msg.body
                print(f"{self.agent.name}: Received request for topic: '{topic_requested}' from {str(msg.sender)}")

                # 1. Find resource
                resource_link = self.agent.get_resource_for_topic(topic_requested)

                # 2. Prepare reply
                # --- FIX: Use make_reply() instead of create_reply() ---
                reply = msg.make_reply()
                reply.set_metadata("performative", "inform")  # As per API

                if resource_link:
                    reply.body = resource_link
                else:
                    reply.body = "ERROR_NOT_FOUND"  # As per API

                # 3. Send reply
                await self.send(reply)
                print(f"{self.agent.name}: Sent reply: {reply.body}")

            else:
                pass