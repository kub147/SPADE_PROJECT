# project/agents/tutor_agent.py
# (COMPLETE VERSION - INCLUDES DIRECTORY AND MONITOR LOGIC)

import asyncio
import json
import random
import time
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# Protocol definitions (must be consistent)
PROTOCOL_CONTRACT_NET = "fipa-contract-net"
PROTOCOL_DIRECTORY = "DirectoryProtocol"
DIRECTORY_AGENT_JID = "directory@localhost"
MONITOR_AGENT_JID = "monitor@localhost"


class TutorAgent(Agent):
    """
    Implements the tutor logic (CNP server).
    - Manages workload (availability).
    - Makes proposals with priority logic.
    - Registers with the DirectoryAgent on startup.
    - Reports sessions to the MonitorAgent.
    """

    async def setup(self):
        # --- Tutor Profile ---
        self.is_available = True
        self.expertise = self.get("expertise") or []  # Will be set from main.py
        self.session_queue_length = 0
        
        # --- CNP Behaviour ---
        cnp_template = Template()
        cnp_template.set_metadata("protocol", PROTOCOL_CONTRACT_NET)
        self.add_behaviour(self.CNPResponderBehav(), cnp_template)

        # --- Register with Directory Agent ---
        self.add_behaviour(self.RegisterWithDirectoryBehav())
        
        print(f"{self.name}: Ready. Available: {self.is_available}. Expertise: {self.expertise}")

    # --- NEW BEHAVIOUR ---
    class RegisterWithDirectoryBehav(OneShotBehaviour):
        """
        A one-shot behaviour to register the tutor's expertise
        with the DirectoryAgent upon startup.
        """
        async def run(self):
            print(f"{self.agent.name}: Registering with Directory...")
            msg = Message(to=DIRECTORY_AGENT_JID)
            msg.set_metadata("protocol", PROTOCOL_DIRECTORY)
            msg.set_metadata("performative", "register")
            msg.body = json.dumps(self.agent.expertise)
            
            await self.send(msg)
            print(f"{self.agent.name}: Registration message sent.")

    def can_help(self, topic):
        """Checks if the tutor can help."""
        return topic in self.expertise

    class CNPResponderBehav(CyclicBehaviour):
        """
        Behaviour to handle the server-side of Contract Net Protocol.
        """

        async def run(self):
            msg = await self.receive(timeout=100)
            if not msg:
                return

            performative = msg.get_metadata("performative")

            if performative == "cfp":
                topic = msg.body
                print(f"{self.agent.name}: Received CFP for {topic}")

                if self.agent.can_help(topic):
                    print(f"{self.agent.name}: Can help. Sending proposal.")
                    reply = msg.make_reply()
                    reply.set_metadata("performative", "propose")

                    # --- Priority Logic ---
                    wait_time = (self.agent.session_queue_length * 5) + 5 

                    base_expertise = 0.9 if self.agent.is_available else 0.7

                    offer = {
                        "wait_time": wait_time,
                        "expertise_level": base_expertise
                    }
                    reply.body = json.dumps(offer)
                    await self.send(reply)
                else:
                    print(f"{self.agent.name}: Cannot help (no expertise).")

            elif performative == "accept-proposal":
                # --- Workload Management ---
                print(f"{self.agent.name}: Proposal ACCEPTED.")
                self.agent.session_queue_length += 1
                self.agent.is_available = False  

                # --- NEW: Report session start to monitor ---
                monitor_msg = Message(to=MONITOR_AGENT_JID)
                monitor_msg.set_metadata("protocol", "MonitorProtocol")
                monitor_msg.set_metadata("performative", "inform")
                monitor_msg.body = json.dumps({
                    "event": "SESSION_START",
                    "tutor": str(self.agent.jid),
                    "student": str(msg.sender),
                    "timestamp": time.time()
                })
                await self.send(monitor_msg)

                # Confirm to student
                reply = msg.make_reply()
                reply.set_metadata("performative", "inform")
                reply.body = "OK, starting session."
                await self.send(reply)

                # Simulate session
                print(f"{self.agent.name}: Conducting session... (Queue: {self.agent.session_queue_length})")
                await asyncio.sleep(random.randint(10, 20))  # Session duration

                self.agent.session_queue_length -=1
                if self.agent.session_queue_length ==0:
                    self.agent.is_available = True  # Free up
                
                print(f"{self.agent.name}: Session finished. (Queue: {self.agent.session_queue_length}). Available: {self.agent.is_available}")

            elif performative == "reject-proposal":
                print(f"{self.agent.name}: Proposal REJECTED.")
                # Do nothing, just wait for the next CFP