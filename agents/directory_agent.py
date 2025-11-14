# project/agents/directory_agent.py

import json
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

# Protocol definition
PROTOCOL_DIRECTORY = "DirectoryProtocol"

class DirectoryAgent(Agent):
    """
    Manages a registry of available tutors and their expertise.
    - Tutors register themselves on startup.
    - Students query this agent to find tutors for a specific topic.
    """

    async def setup(self):
        # A simple dictionary to store {jid: [expertise1, expertise2]}
        self.tutor_registry = {}
        print(f"{self.name}: Directory is online.")

        # Template to listen for all directory-related messages
        template = Template()
        template.set_metadata("protocol", PROTOCOL_DIRECTORY)

        self.add_behaviour(self.DirectoryResponderBehav(), template)

    class DirectoryResponderBehav(CyclicBehaviour):
        """
        Handles two types of requests:
        1. 'register': A tutor registers their expertise.
        2. 'query': A student asks for tutors for a topic.
        """

        async def run(self):
            msg = await self.receive(timeout=100)
            if not msg:
                return

            performative = msg.get_metadata("performative")

            try:
                if performative == "register":
                    # A tutor is registering
                    jid = str(msg.sender)
                    expertise = json.loads(msg.body)
                    self.agent.tutor_registry[jid] = expertise
                    print(f"{self.agent.name}: Registered {jid} with expertise {expertise}")

                elif performative == "query":
                    # A student is querying
                    topic = msg.body
                    print(f"{self.agent.name}: Received query for topic '{topic}'")

                    # Find all tutors who have this topic in their expertise list
                    matches = []
                    for jid, expertise_list in self.agent.tutor_registry.items():
                        if topic in expertise_list:
                            matches.append(jid)
                    
                    print(f"{self.agent.name}: Found {len(matches)} matches.")

                    # Reply to the student with the list of matching JIDs
                    reply = msg.make_reply()
                    reply.set_metadata("performative", "inform")
                    reply.body = json.dumps(matches) # Send list as a JSON string
                    await self.send(reply)

            except Exception as e:
                print(f"{self.agent.name}: Error processing message from {msg.sender}: {e}")