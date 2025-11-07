# project/agents/student_agent.py
# (FIXED VERSION)

import asyncio
import json
import random
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message

# --- FSM State Definitions ---
STATE_START = "STATE_START"
STATE_REQUEST_RESOURCES = "STATE_REQUEST_RESOURCES"
STATE_AWAIT_RESOURCES = "STATE_AWAIT_RESOURCES"
STATE_EVALUATE_KNOWLEDGE = "STATE_EVALUATE_KNOWLEDGE"
STATE_START_CNP = "STATE_START_CNP"
STATE_AWAIT_PROPOSALS = "STATE_AWAIT_PROPOSALS"
STATE_SELECT_TUTOR = "STATE_SELECT_TUTOR"
STATE_AWAIT_TUTORING = "STATE_AWAIT_TUTORING"
STATE_FINISH = "STATE_FINISH"

# --- Agent JIDs ---
RESOURCE_AGENT_JID = "resource_manager@localhost"
TUTOR_JIDS = ["tutor1@localhost", "tutor2@localhost"]  # List of tutors to ask


class StudentAgent(Agent):
    """
    Implements the student logic, knowledge profile, and FSM.
    """

    async def setup(self):
        # --- Student Profile ---
        self.topic_needed = "mathematics"
        self.knowledge = 0.1  # Start with 10%
        self.knowledge_goal = 0.9  # Goal is 90%

        # Initialize shared FSM variables on the AGENT
        self.proposals = []
        self.received_resource_effectiveness = 0.0

        print(f"{self.name}: Ready. Topic: '{self.topic_needed}'. Knowledge: {self.knowledge}")

        fsm = StudentFSM()
        # Register states
        fsm.add_state(name=STATE_START, state=StartState(), initial=True)
        fsm.add_state(name=STATE_REQUEST_RESOURCES, state=RequestResourcesState())
        fsm.add_state(name=STATE_AWAIT_RESOURCES, state=AwaitResourcesState())
        fsm.add_state(name=STATE_EVALUATE_KNOWLEDGE, state=EvaluateKnowledgeState())
        fsm.add_state(name=STATE_START_CNP, state=StartCNPState())
        fsm.add_state(name=STATE_AWAIT_PROPOSALS, state=AwaitProposalsState())
        fsm.add_state(name=STATE_SELECT_TUTOR, state=SelectTutorState())
        fsm.add_state(name=STATE_AWAIT_TUTORING, state=AwaitTutoringState())
        fsm.add_state(name=STATE_FINISH, state=FinishState())

        # Define transitions
        fsm.add_transition(source=STATE_START, dest=STATE_REQUEST_RESOURCES)
        fsm.add_transition(source=STATE_REQUEST_RESOURCES, dest=STATE_AWAIT_RESOURCES)
        fsm.add_transition(source=STATE_AWAIT_RESOURCES, dest=STATE_EVALUATE_KNOWLEDGE)
        fsm.add_transition(source=STATE_EVALUATE_KNOWLEDGE, dest=STATE_FINISH)
        fsm.add_transition(source=STATE_EVALUATE_KNOWLEDGE, dest=STATE_START_CNP)
        fsm.add_transition(source=STATE_START_CNP, dest=STATE_AWAIT_PROPOSALS)
        fsm.add_transition(source=STATE_AWAIT_PROPOSALS, dest=STATE_SELECT_TUTOR)
        fsm.add_transition(source=STATE_AWAIT_PROPOSALS, dest=STATE_START)  # No proposals
        fsm.add_transition(source=STATE_SELECT_TUTOR, dest=STATE_AWAIT_TUTORING)
        fsm.add_transition(source=STATE_AWAIT_TUTORING, dest=STATE_EVALUATE_KNOWLEDGE)  # Re-evaluate after tutoring

        self.add_behaviour(fsm)

    def is_goal_met(self):
        return self.knowledge >= self.knowledge_goal


# ######################################################################
# FSM (Finite State Machine) and its States
# ######################################################################

class StudentFSM(FSMBehaviour):
    """The main FSM managing the student's logic."""

    async def on_start(self):
        print(f"{self.agent.name}: Starting FSM...")

    async def on_end(self):
        print(f"{self.agent.name}: FSM finished. Final knowledge: {self.agent.knowledge:.2f}")
        await self.agent.stop()


# --- State Definitions ---

class StartState(State):
    async def run(self):
        print(f"{self.agent.name}: State: START. Knowledge: {self.agent.knowledge:.2f}")
        await asyncio.sleep(1)
        self.set_next_state(STATE_REQUEST_RESOURCES)


class RequestResourcesState(State):
    async def run(self):
        print(f"{self.agent.name}: State: REQUEST_RESOURCES. Asking for '{self.agent.topic_needed}'")
        msg = Message(to=RESOURCE_AGENT_JID)
        msg.set_metadata("protocol", "ResourceProtocol")
        msg.set_metadata("performative", "request")
        msg.body = self.agent.topic_needed
        await self.send(msg)
        self.set_next_state(STATE_AWAIT_RESOURCES)


class AwaitResourcesState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_RESOURCES. Waiting for resource...")
        msg = await self.receive(timeout=5)

        if msg and "ERROR" not in msg.body:
            print(f"{self.agent.name}: Received resource: {msg.body}")
            self.agent.received_resource_effectiveness = 0.4  # This resource gives 0.4 knowledge
        else:
            print(f"{self.agent.name}: Did not receive resource or timeout.")
            self.agent.received_resource_effectiveness = 0.0

        self.set_next_state(STATE_EVALUATE_KNOWLEDGE)


class EvaluateKnowledgeState(State):
    async def run(self):
        print(f"{self.agent.name}: State: EVALUATE_KNOWLEDGE.")

        if self.agent.received_resource_effectiveness > 0:
            print(f"{self.agent.name}: Studying the received resource...")
            await asyncio.sleep(3)  # Study time
            self.agent.knowledge += self.agent.received_resource_effectiveness
            self.agent.received_resource_effectiveness = 0.0  # Reset after use
            print(f"{self.agent.name}: Knowledge after studying: {self.agent.knowledge:.2f}")

        if self.agent.is_goal_met():
            print(f"{self.agent.name}: Knowledge goal met!")
            self.set_next_state(STATE_FINISH)
        else:
            print(f"{self.agent.name}: Still need help. Looking for a tutor.")
            self.set_next_state(STATE_START_CNP)


class StartCNPState(State):
    async def run(self):
        print(f"{self.agent.name}: State: START_CNP. Sending CFP for '{self.agent.topic_needed}'")
        self.agent.proposals = []

        # --- FIX: Send one message per tutor, not one message to a list ---
        print(f"{self.agent.name}: Sending CFP to {TUTOR_JIDS}")
        for tutor_jid in TUTOR_JIDS:
            msg = Message(to=tutor_jid)  # Set 'to' in the constructor
            msg.set_metadata("protocol", "fipa-contract-net")
            msg.set_metadata("performative", "cfp")
            msg.body = self.agent.topic_needed
            await self.send(msg)

        self.set_next_state(STATE_AWAIT_PROPOSALS)


class AwaitProposalsState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_PROPOSALS. Collecting offers (5s)...")
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 5.0:
            msg = await self.receive(timeout=1.0)
            if msg and msg.get_metadata("performative") == "propose":
                print(f"{self.agent.name}: Received proposal from {str(msg.sender)}")
                self.agent.proposals.append(msg)

        if not self.agent.proposals:
            print(f"{self.agent.name}: No proposals received. Will try again later.")
            await asyncio.sleep(10)
            self.set_next_state(STATE_START)
        else:
            self.set_next_state(STATE_SELECT_TUTOR)


class SelectTutorState(State):
    async def run(self):
        print(f"{self.agent.name}: State: SELECT_TUTOR. Selecting best proposal...")

        best_proposal = None
        best_score = float('inf')

        for msg in self.agent.proposals:
            try:
                offer = json.loads(msg.body)
                wait_time = offer.get("wait_time", 99)

                if wait_time < best_score:
                    best_score = wait_time
                    best_proposal = msg
            except Exception as e:
                print(f"{self.agent.name}: Bad proposal from {str(msg.sender)}: {e}")

        if best_proposal:
            print(f"{self.agent.name}: Accepting proposal from {str(best_proposal.sender)} (score: {best_score})")

            # Accept best
            # --- FIX: Use make_reply() ---
            reply = best_proposal.make_reply()
            reply.set_metadata("performative", "accept-proposal")
            await self.send(reply)

            # Reject others
            for msg in self.agent.proposals:
                if msg.sender != best_proposal.sender:
                    # --- FIX: Use make_reply() ---
                    reject_reply = msg.make_reply()
                    reject_reply.set_metadata("performative", "reject-proposal")
                    await self.send(reject_reply)

            self.set_next_state(STATE_AWAIT_TUTORING)
        else:
            print(f"{self.agent.name}: Could not select a proposal.")
            self.set_next_state(STATE_START)


class AwaitTutoringState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_TUTORING. Waiting for confirmation...")
        msg = await self.receive(timeout=10)

        if msg and msg.get_metadata("performative") == "inform":
            print(f"{self.agent.name}: Tutor {str(msg.sender)} started session.")
            await asyncio.sleep(5)  # Simulating session
            self.agent.knowledge = 1.0  # Tutor always gives 100% knowledge
            print(f"{self.agent.name}: Session finished.")
        else:
            print(f"{self.agent.name}: Tutor did not confirm session.")

        self.set_next_state(STATE_EVALUATE_KNOWLEDGE)  # Re-evaluate knowledge


class FinishState(State):
    async def run(self):
        print(f"{self.agent.name}: State: FINISH. Goal achieved.")
        # The FSM will now stop