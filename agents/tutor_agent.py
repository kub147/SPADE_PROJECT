# project/agents/tutor_agent.py
# (FIXED VERSION)

import asyncio
import json
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from spade.template import Template

# Protocol definitions (must be consistent)
PROTOCOL_CONTRACT_NET = "fipa-contract-net"


class TutorAgent(Agent):
    """
    Implements the tutor logic (CNP server).
    - Manages workload (availability).
    - Makes proposals with priority logic.
    """

    async def setup(self):
        # --- Tutor Profile ---
        self.is_available = True
        self.expertise = self.get("expertise") or []  # Will be set from main.py
        print(f"{self.name}: Ready. Available: {self.is_available}. Expertise: {self.expertise}")

        # Template to listen for CNP messages
        cnp_template = Template()
        cnp_template.set_metadata("protocol", PROTOCOL_CONTRACT_NET)

        self.add_behaviour(self.CNPResponderBehav(), cnp_template)

    def can_help(self, topic):
        """Checks if the tutor can help."""
        return self.is_available and topic in self.expertise

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
                    # --- FIX: Use make_reply() ---
                    reply = msg.make_reply()
                    reply.set_metadata("performative", "propose")

                    # --- Priority Logic ---
                    wait_time = random.randint(1, 10)

                    offer = {
                        "wait_time": wait_time,
                        "expertise_level": 0.9
                    }
                    reply.body = json.dumps(offer)  # As per API
                    await self.send(reply)
                else:
                    print(f"{self.agent.name}: Cannot help (busy or no expertise).")

            elif performative == "accept-proposal":
                # --- Workload Management ---
                print(f"{self.agent.name}: Proposal ACCEPTED.")
                self.agent.is_available = False  # Key! Become busy.

                # Confirm to student
                # --- FIX: Use make_reply() ---
                reply = msg.make_reply()
                reply.set_metadata("performative", "inform")
                reply.body = "OK, starting session."
                await self.send(reply)

                # Simulate session
                print(f"{self.agent.name}: Conducting session...")
                await asyncio.sleep(random.randint(10, 20))  # Session duration

                print(f"{self.agent.name}: Session finished. Becoming available again.")
                self.agent.is_available = True  # Free up

            elif performative == "reject-proposal":
                print(f"{self.agent.name}: Proposal REJECTED.")
                # Do nothing, just wait for the next CFP