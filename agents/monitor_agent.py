# project/agents/monitor_agent.py
# (MODIFIED - ADDS FINAL LEARNING SUMMARY)

import json
import time
import numpy as np
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template

# Protocol definition
PROTOCOL_MONITOR = "MonitorProtocol"
MONITOR_AGENT_JID = "monitor@localhost"


class MonitorAgent(Agent):
    """
    Passively monitors the system by collecting event logs.
    Calculates and prints performance metrics on shutdown.
    """

    async def setup(self):
        self.event_log = []
        self.start_time = time.time()
        print(f"{self.name}: Monitor is online. Logging events...")

        # Template to listen for all 'inform' messages
        template = Template()
        template.set_metadata("protocol", PROTOCOL_MONITOR)
        template.set_metadata("performative", "inform")

        self.add_behaviour(self.LogEventBehav(), template)

    def takedown(self):
        """
        Called when the agent is stopped.
        This is where we calculate and print all metrics.
        """
        print("\n" + "="*50)
        print(f"--- SYSTEM PERFORMANCE METRICS ---")
        print(f"Simulation finished. Total runtime: {time.time() - self.start_time:.2f}s")
        print(f"Total events logged: {len(self.event_log)}")
        print("="*50 + "\n")

        # --- Dictionaries to store processed data ---
        self.starts = {e['student']: e for e in self.event_log if e['event'] == 'STUDENT_START'}
        self.ends = {e['student']: e for e in self.event_log if e['event'] == 'STUDENT_FINISH'}

        # --- Run all metric calculations ---
        self.calculate_resource_utilization()
        self.calculate_tutor_workload()
        self.calculate_time_to_help()
        self.calculate_learning_gains()
        self.summarize_student_learning() # <-- NEW SUMMARY

        print("="*50)
        print("--- End of Report ---")
        
        return super().takedown()

    def calculate_resource_utilization(self):
        """Metric: Resource utilization efficiency"""
        resource_uses = [e for e in self.event_log if e['event'] == 'RESOURCE_PROVIDED']
        print(f"### 1. Resource Utilization")
        print(f"* Total resources provided: {len(resource_uses)}")
        # ... (rest of function is the same) ...
        print("\n")

    def calculate_tutor_workload(self):
        """Metric: Tutor workload balance"""
        sessions = [e for e in self.event_log if e['event'] == 'SESSION_START']
        workload = {}
        for s in sessions:
            tutor = s['tutor'].split('@')[0]
            workload[tutor] = workload.get(tutor, 0) + 1
        
        print(f"### 2. Tutor Workload Balance")
        print(f"* Total tutoring sessions: {len(sessions)}")
        if workload:
            for tutor, count in workload.items():
                print(f"    - {tutor}: {count} session(s)")
        else:
            print(f"    - No tutors were engaged.")
        print("\n")

    def calculate_time_to_help(self):
        """Metric: Average time to resolve learning difficulties"""
        help_requests = {e['student']: e['timestamp'] for e in self.event_log if e['event'] == 'STUDENT_REQUEST_HELP'}
        tutor_founds = {e['student']: e['timestamp'] for e in self.event_log if e['event'] == 'STUDENT_FOUND_TUTOR'}
        
        timings = []
        for student_jid, start_time in help_requests.items():
            if student_jid in tutor_founds:
                end_time = tutor_founds[student_jid]
                timings.append(end_time - start_time)
        
        print(f"### 3. Time to Resolve Difficulties")
        if timings:
            print(f"* Average time to find a tutor: {np.mean(timings):.2f}s")
            print(f"* Max time: {np.max(timings):.2f}s / Min time: {np.min(timings):.2f}s")
        else:
            print(f"* No tutor requests were successfully resolved.")
        print("\n")
        
    def calculate_learning_gains(self):
        """Metric: Student learning gains"""
        gains = []
        for student_jid, start_event in self.starts.items():
            if student_jid in self.ends:
                end_event = self.ends[student_jid]
                gain = end_event['knowledge'] - start_event['knowledge']
                gains.append(gain)
                
        print(f"### 4. Student Learning Gains")
        if gains:
            print(f"* Average knowledge gain: {np.mean(gains):.2f}")
        else:
            print(f"* No student lifecycles were completed.")
        print("\n")

    # ######################################################################
    # --- THIS IS THE NEW FUNCTION ---
    # ######################################################################
    def summarize_student_learning(self):
        """Summary of which students learned what."""
        print(f"### 5. Student Learning Summary")
        
        completed_count = 0
        for student_jid, start_event in self.starts.items():
            student_name = student_jid.split('@')[0]
            topic = start_event['topic']
            
            if student_jid in self.ends:
                # This student finished
                print(f"    - ✅ {student_name}: Successfully learned '{topic}'")
                completed_count += 1
            else:
                # This student did not finish
                print(f"    - ❌ {student_name}: Did NOT finish learning '{topic}'")

        if not self.starts:
            print("    - No students started the learning process.")
        
        print(f"\n* Total completed: {completed_count} / {len(self.starts)}")
        print("\n")


    class LogEventBehav(CyclicBehaviour):
        """
        This behaviour runs forever, listening for messages
        matching the template and adding them to the agent's log.
        """
        async def run(self):
            msg = await self.receive(timeout=1000)
            if msg:
                try:
                    data = json.loads(msg.body)
                    print(f"[Monitor]: Logged '{data['event']}'")
                    # Add timestamp *at time of logging* for accuracy
                    data['log_time'] = time.time()
                    self.agent.event_log.append(data)
                except Exception as e:
                    print(f"{self.agent.name}: Error processing log message: {e}")