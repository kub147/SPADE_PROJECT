# project/agents/student_agent.py
# (COMPLETE VERSION - INCLUDES ATTENTION SPAN & BANDWIDTH HANDLING)

import asyncio
import json
import random
import time
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, OneShotBehaviour
from spade.message import Message
from spade.template import Template

# --- FSM State Definitions ---
STATE_START = "STATE_START"
STATE_REQUEST_RESOURCES = "STATE_REQUEST_RESOURCES"
STATE_AWAIT_RESOURCES = "STATE_AWAIT_RESOURCES"
STATE_EVALUATE_KNOWLEDGE = "STATE_EVALUATE_KNOWLEDGE"
STATE_QUERY_DIRECTORY = "STATE_QUERY_DIRECTORY"
STATE_AWAIT_DIRECTORY = "STATE_AWAIT_DIRECTORY"
STATE_START_CNP = "STATE_START_CNP"
STATE_AWAIT_PROPOSALS = "STATE_AWAIT_PROPOSALS"
STATE_SELECT_TUTOR = "STATE_SELECT_TUTOR"
STATE_AWAIT_TUTORING = "STATE_AWAIT_TUTORING"
STATE_TAKE_BREAK = "STATE_TAKE_BREAK"  
STATE_FINISH = "STATE_FINISH"

# --- Agent JIDs ---
RESOURCE_AGENT_JID = "resource_manager@localhost"
DIRECTORY_AGENT_JID = "directory@localhost"
MONITOR_AGENT_JID = "monitor@localhost"

# --- Protocol Definitions (for matching) ---
PROTOCOL_RESOURCE = "ResourceProtocol"
PROTOCOL_CNP = "fipa-contract-net"
PROTOCOL_DIRECTORY = "DirectoryProtocol"


class StudentAgent(Agent):
    """
    Implements the student logic, knowledge profile, and FSM.
    - Queries the DirectoryAgent to find tutors.
    - Reports key events to the MonitorAgent.
    - Manages an "attention span" and must take breaks.
    - Handles resource server "busy" errors.
    """

    async def setup(self):
        # --- Student Profile ---
        self.topic_needed = self.get("topic_needed") or "biology"
        self.knowledge = self.get("knowledge") or 0.1
        self.knowledge_goal = 0.9
        self.attention = 100  

        # Initialize shared FSM variables
        self.proposals = []
        self.received_resource_effectiveness = 0.0
        self.available_tutors = []
        self.selected_tutor = None

        print(f"{self.name}: Ready. Topic: '{self.topic_needed}'. Knowledge: {self.knowledge}. Attention: {self.attention}%")

        fsm = StudentFSM()
        # Register states
        fsm.add_state(name=STATE_START, state=StartState(), initial=True)
        fsm.add_state(name=STATE_REQUEST_RESOURCES, state=RequestResourcesState())
        fsm.add_state(name=STATE_AWAIT_RESOURCES, state=AwaitResourcesState())
        fsm.add_state(name=STATE_EVALUATE_KNOWLEDGE, state=EvaluateKnowledgeState())
        fsm.add_state(name=STATE_QUERY_DIRECTORY, state=QueryDirectoryState())
        fsm.add_state(name=STATE_AWAIT_DIRECTORY, state=AwaitDirectoryState())
        fsm.add_state(name=STATE_START_CNP, state=StartCNPState())
        fsm.add_state(name=STATE_AWAIT_PROPOSALS, state=AwaitProposalsState())
        fsm.add_state(name=STATE_SELECT_TUTOR, state=SelectTutorState())
        fsm.add_state(name=STATE_AWAIT_TUTORING, state=AwaitTutoringState())
        fsm.add_state(name=STATE_TAKE_BREAK, state=TakeBreakState()) 
        fsm.add_state(name=STATE_FINISH, state=FinishState())

        # Define transitions
        fsm.add_transition(source=STATE_START, dest=STATE_REQUEST_RESOURCES)
        fsm.add_transition(source=STATE_REQUEST_RESOURCES, dest=STATE_AWAIT_RESOURCES)
        fsm.add_transition(source=STATE_AWAIT_RESOURCES, dest=STATE_EVALUATE_KNOWLEDGE)
        fsm.add_transition(source=STATE_AWAIT_RESOURCES, dest=STATE_REQUEST_RESOURCES) # For server busy
        
        # --- THIS IS THE FIX ---
        # Allow the state to transition to itself to re-queue bad messages
        fsm.add_transition(source=STATE_AWAIT_RESOURCES, dest=STATE_AWAIT_RESOURCES)

        fsm.add_transition(source=STATE_EVALUATE_KNOWLEDGE, dest=STATE_FINISH)
        fsm.add_transition(source=STATE_EVALUATE_KNOWLEDGE, dest=STATE_TAKE_BREAK)
        fsm.add_transition(source=STATE_EVALUATE_KNOWLEDGE, dest=STATE_QUERY_DIRECTORY)
        fsm.add_transition(source=STATE_TAKE_BREAK, dest=STATE_EVALUATE_KNOWLEDGE)
        fsm.add_transition(source=STATE_QUERY_DIRECTORY, dest=STATE_AWAIT_DIRECTORY)
        fsm.add_transition(source=STATE_AWAIT_DIRECTORY, dest=STATE_START_CNP)
        fsm.add_transition(source=STATE_AWAIT_DIRECTORY, dest=STATE_START)
        fsm.add_transition(source=STATE_START_CNP, dest=STATE_AWAIT_PROPOSALS)
        fsm.add_transition(source=STATE_AWAIT_PROPOSALS, dest=STATE_SELECT_TUTOR)
        fsm.add_transition(source=STATE_AWAIT_PROPOSALS, dest=STATE_START)
        fsm.add_transition(source=STATE_SELECT_TUTOR, dest=STATE_AWAIT_TUTORING)
        fsm.add_transition(source=STATE_AWAIT_TUTORING, dest=STATE_EVALUATE_KNOWLEDGE)
        fsm.add_transition(source=STATE_AWAIT_TUTORING, dest=STATE_START)

        self.add_behaviour(fsm)
        self.add_behaviour(self.ReportStartBehav())

    class ReportStartBehav(OneShotBehaviour):
        async def run(self):
            msg = Message(to=MONITOR_AGENT_JID)
            msg.set_metadata("protocol", "MonitorProtocol")
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps({
                "event": "STUDENT_START", "student": str(self.agent.jid),
                "knowledge": self.agent.knowledge, "goal": self.agent.knowledge_goal,
                "topic": self.agent.topic_needed, "timestamp": time.time()
            })
            await self.send(msg)
    
    def is_goal_met(self):
        return self.knowledge >= self.knowledge_goal

class StudentFSM(FSMBehaviour):
    async def on_start(self): print(f"{self.agent.name}: Starting FSM...")
    async def on_end(self):
        print(f"{self.agent.name}: FSM finished. Final knowledge: {self.agent.knowledge:.2f}")
        await self.agent.stop()

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
        self.agent.received_resource_effectiveness = 0.0

        template = Template()
        template.set_metadata("protocol", PROTOCOL_RESOURCE)
        template.sender = RESOURCE_AGENT_JID
        self.set_template(template)
        
        msg = await self.receive(timeout=30) 

        # Check for wrong protocol
        if msg and msg.get_metadata("protocol") != PROTOCOL_RESOURCE:
            print(f"{self.agent.name}: State: AWAIT_RESOURCES. Received WRONG protocol ({msg.get_metadata('protocol')}). Re-queueing.")
            # This message is not for us. Transition to self to re-run the state.
            self.set_next_state(STATE_AWAIT_RESOURCES) # This transition is now registered
            return

        # Process the (correct) message
        if msg:
            performative = msg.get_metadata("performative")
            if performative == "inform":
                print(f"{self.agent.name}: Received resource: {msg.body}")
                self.agent.received_resource_effectiveness = 0.4
            
            elif performative == "failure" or "ERROR_SERVER_BUSY" in msg.body:
                print(f"{self.agent.name}: Resource server is busy. Will try again later.")
                await asyncio.sleep(10)
                self.set_next_state(STATE_REQUEST_RESOURCES) # Go back and ask again
                return
                
            else:
                print(f"{self.agent.name}: Did not receive resource or received error: {msg.body}")
        else:
            print(f"{self.agent.name}: Resource request timed out. Moving on without it.")

        self.set_next_state(STATE_EVALUATE_KNOWLEDGE)



class EvaluateKnowledgeState(State):
    async def run(self):
        print(f"{self.agent.name}: State: EVALUATE_KNOWLEDGE. (Attention: {self.agent.attention}%)")

        if self.agent.received_resource_effectiveness > 0:
            print(f"{self.agent.name}: Studying the received resource...")
            await asyncio.sleep(3)  # Study time

            # --- NEW: Calculate gain based on attention ---
            effectiveness_multiplier = self.agent.attention / 100
            gain = self.agent.received_resource_effectiveness * effectiveness_multiplier
            
            self.agent.knowledge += gain
            self.agent.received_resource_effectiveness = 0.0  # Reset
            self.agent.attention -= 30 # Studying costs attention
            
            print(f"{self.agent.name}: Gained {gain:.2f} knowledge. (New total: {self.agent.knowledge:.2f})")
            print(f"{self.agent.name}: Attention is now {self.agent.attention}%.")

        # Check outcomes in order
        if self.agent.is_goal_met():
            print(f"{self.agent.name}: Knowledge goal met!")
            self.set_next_state(STATE_FINISH)
        
        elif self.agent.attention < 20:
            print(f"{self.agent.name}: Attention too low. Taking a break.")
            self.set_next_state(STATE_TAKE_BREAK)
            
        else:
            print(f"{self.agent.name}: Still need help. Querying directory.")
            msg = Message(to=MONITOR_AGENT_JID)
            msg.set_metadata("protocol", "MonitorProtocol")
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps({
                "event": "STUDENT_REQUEST_HELP", "student": str(self.agent.jid),
                "topic": self.agent.topic_needed, "timestamp": time.time()
            })
            await self.send(msg)
            self.set_next_state(STATE_QUERY_DIRECTORY)


class QueryDirectoryState(State):
    async def run(self):
        print(f"{self.agent.name}: State: QUERY_DIRECTORY. Asking for '{self.agent.topic_needed}' tutors.")
        msg = Message(to=DIRECTORY_AGENT_JID)
        msg.set_metadata("protocol", "DirectoryProtocol")
        msg.set_metadata("performative", "query")
        msg.body = self.agent.topic_needed
        await self.send(msg)
        self.set_next_state(STATE_AWAIT_DIRECTORY)

class AwaitDirectoryState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_DIRECTORY. Waiting for tutor list...")
        msg = await self.receive(timeout=5)
        if msg and msg.get_metadata("performative") == "inform":
            try:
                self.agent.available_tutors = json.loads(msg.body)
                if self.agent.available_tutors:
                    print(f"{self.agent.name}: Received {len(self.agent.available_tutors)} tutors from directory.")
                    self.set_next_state(STATE_START_CNP)
                else:
                    print(f"{self.agent.name}: Directory found no tutors. Trying again later.")
                    await asyncio.sleep(10); self.set_next_state(STATE_START)
            except Exception as e:
                print(f"{self.agent.name}: Failed to parse directory response: {e}")
                self.set_next_state(STATE_START)
        else:
            print(f"{self.agent.name}: Directory did not reply. Trying again later.")
            await asyncio.sleep(10); self.set_next_state(STATE_START)


class StartCNPState(State):
    async def run(self):
        tutors_to_contact = self.agent.available_tutors
        if not tutors_to_contact:
            print(f"{self.agent.name}: State: START_CNP. No tutors found. Skipping.")
            self.set_next_state(STATE_START); return
        print(f"{self.agent.name}: State: START_CNP. Sending CFP for '{self.agent.topic_needed}' to {tutors_to_contact}")
        self.agent.proposals = []
        for tutor_jid in tutors_to_contact:
            msg = Message(to=tutor_jid)
            msg.set_metadata("protocol", "fipa-contract-net")
            msg.set_metadata("performative", "cfp")
            msg.body = self.agent.topic_needed
            await self.send(msg)
        self.set_next_state(STATE_AWAIT_PROPOSALS)

class AwaitProposalsState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_PROPOSALS. Collecting offers (5s)...")
        start_time = asyncio.get_event_loop().time()
        
        template = Template()
        template.set_metadata("protocol", PROTOCOL_CNP)
        template.set_metadata("performative", "propose")
        self.set_template(template)
        
        while asyncio.get_event_loop().time() - start_time < 5.0:
            msg = await self.receive(timeout=1.0)
            
            # --- THE FIX: Check the protocol again, just in case ---
            if msg and msg.get_metadata("protocol") == PROTOCOL_CNP and msg.get_metadata("performative") == "propose":
                print(f"{self.agent.name}: Received proposal from {str(msg.sender)}")
                self.agent.proposals.append(msg)
            elif msg:
                print(f"{self.agent.name}: State: AWAIT_PROPOSALS. Received WRONG protocol ({msg.get_metadata('protocol')}). Ignoring.")
                # This message will be handled later
        
        if not self.agent.proposals:
            print(f"{self.agent.name}: No proposals received. Will try again later.")
            await asyncio.sleep(10); self.set_next_state(STATE_START)
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
                expertise = offer.get("expertise_level", 0.1)
                score = wait_time + ((1 - expertise) * 20)
                print(f"{self.agent.name}: Evaluated {str(msg.sender)}: wait={wait_time}, expertise={expertise}, score={score:.2f}")
                if score < best_score:
                    best_score = score
                    best_proposal = msg
            except Exception as e:
                print(f"{self.agent.name}: Bad proposal from {str(msg.sender)}: {e}")
        
        if best_proposal:
            print(f"{self.agent.name}: Accepting proposal from {str(best_proposal.sender)} (best score: {best_score:.2f})")
            
            # --- NEW: Store the JID of the tutor we are waiting for ---
            self.agent.selected_tutor = str(best_proposal.sender) 

            # ... (send monitor report) ...
            msg = Message(to=MONITOR_AGENT_JID)
            msg.set_metadata("protocol", "MonitorProtocol")
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps({
                "event": "STUDENT_FOUND_TUTOR", "student": str(self.agent.jid),
                "tutor": str(best_proposal.sender), "timestamp": time.time()
            })
            await self.send(msg)
            
            # ... (accept/reject logic is the same) ...
            reply = best_proposal.make_reply()
            reply.set_metadata("performative", "accept-proposal")
            await self.send(reply)
            for msg in self.agent.proposals:
                if msg.sender != best_proposal.sender:
                    reject_reply = msg.make_reply()
                    reject_reply.set_metadata("performative", "reject-proposal")
                    await self.send(reject_reply)
            
            self.set_next_state(STATE_AWAIT_TUTORING)
        else:
            print(f"{self.agent.name}: Could not select a proposal.")
            self.set_next_state(STATE_START)


class AwaitTutoringState(State):
    async def run(self):
        print(f"{self.agent.name}: State: AWAIT_TUTORING. Waiting for confirmation from {self.agent.selected_tutor}...")

        # --- Use a Template to ONLY match the inform from the selected tutor ---
        template = Template()
        template.set_metadata("protocol", PROTOCOL_CNP)
        template.set_metadata("performative", "inform")
        template.sender = self.agent.selected_tutor
        
        self.set_template(template) # <-- SET TEMPLATE HERE
        msg = await self.receive(timeout=20) # <-- REMOVED FROM HERE

        if msg:
            print(f"{self.agent.name}: Tutor {str(msg.sender)} started session.")
            await asyncio.sleep(5)
            self.agent.knowledge = 1.0
            self.agent.attention -= 20
            print(f"{self.agent.name}: Session finished. Attention: {self.agent.attention}%")
        else:
            print(f"{self.agent.name}: Tutor did not confirm session. Will retry.")
            self.agent.selected_tutor = None # Clear selection
            self.set_next_state(STATE_START) # Go back to start
            return

        self.set_next_state(STATE_EVALUATE_KNOWLEDGE)


class TakeBreakState(State):
    async def run(self):
        print(f"{self.agent.name}: State: TAKE_BREAK. Resting to restore attention...")
        await asyncio.sleep(10) # 10 second break
        self.agent.attention = 100 # Attention fully restored
        print(f"{self.agent.name}: Break over. Attention restored to 100%.")
        self.set_next_state(STATE_EVALUATE_KNOWLEDGE) # Go back to check if goal is met


class FinishState(State):
    async def run(self):
        print(f"{self.agent.name}: State: FINISH. Goal achieved.")
        msg = Message(to=MONITOR_AGENT_JID)
        msg.set_metadata("protocol", "MonitorProtocol")
        msg.set_metadata("performative", "inform")
        msg.body = json.dumps({
            "event": "STUDENT_FINISH", "student": str(self.agent.jid),
            "knowledge": self.agent.knowledge, "timestamp": time.time()
        })
        await self.send(msg)
        # The FSM will now stop