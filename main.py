# project/main.py
# (MODIFIED VERSION - LAUNCHES MULTIPLE STUDENTS)

import asyncio
import spade
import random
from spade.behaviour import PeriodicBehaviour

# Import agent classes
from agents.student_agent import StudentAgent
from agents.tutor_agent import TutorAgent
from agents.resource_agent import ResourceAgent
from agents.directory_agent import DirectoryAgent
from agents.monitor_agent import MonitorAgent

# ... (DynamicEnvironmentBehav class remains the same) ...
class DynamicEnvironmentBehav(PeriodicBehaviour):
    async def run(self):
        if not self.agent.tutors:
            return
        tutor_to_change = random.choice(self.agent.tutors)
        new_availability = random.choice([True, False])
        tutor_to_change.is_available = new_availability
        print(f"[Environment]: Tutor {tutor_to_change.name}'s availability changed to: {new_availability}")


async def main():
    print("Starting the multi-agent system...")

    # A list to keep track of all server agents
    agents = []

    # --- (All agent startup logic is the same) ---
    monitor = MonitorAgent("monitor@localhost", "password")
    await monitor.start(auto_register=True)
    agents.append(monitor)
    print("Monitor Agent started.")

    directory = DirectoryAgent("directory@localhost", "password")
    await directory.start(auto_register=True)
    agents.append(directory)
    print("Directory Agent started.")

    resource_mgr = ResourceAgent("resource_manager@localhost", "password")
    await resource_mgr.start(auto_register=True)
    agents.append(resource_mgr)

    tutor1 = TutorAgent("tutor1@localhost", "password")
    tutor1.set("expertise", ["mathematics", "physics"])
    await tutor1.start(auto_register=True)
    agents.append(tutor1)

    tutor2 = TutorAgent("tutor2@localhost", "password")
    tutor2.set("expertise", ["physics"])
    await tutor2.start(auto_register=True)
    agents.append(tutor2)
    
    tutor3 = TutorAgent("tutor3@localhost", "password")
    tutor3.set("expertise", ["biology", "history"])
    await tutor3.start(auto_register=True)
    agents.append(tutor3)
    print("Tutor agents started and registered.")

    environment_agent = spade.agent.Agent("environment@localhost", "password")
    environment_agent.tutors = [tutor1, tutor2, tutor3] 
    await environment_agent.start(auto_register=True)
    env_behav = DynamicEnvironmentBehav(period=30)
    environment_agent.add_behaviour(env_behav)
    agents.append(environment_agent)
    
    print("Server agents started. Waiting 5s before launching students...")
    await asyncio.sleep(5) 

    student_agents = []

    # --- (Creating all 5 students is the same) ---
    student1 = StudentAgent("student1@localhost", "password")
    student1.set("topic_needed", "biology") # Changed for this test
    student1.set("knowledge", 0.1)
    await student1.start(auto_register=True)
    student_agents.append(student1)

    student2 = StudentAgent("student2@localhost", "password")
    student2.set("topic_needed", "mathematics")
    student2.set("knowledge", 0.3)
    await student2.start(auto_register=True)
    student_agents.append(student2)

    student3 = StudentAgent("student3@localhost", "password")
    student3.set("topic_needed", "history")
    student3.set("knowledge", 0.2)
    await student3.start(auto_register=True)
    student_agents.append(student3)

    student4 = StudentAgent("student4@localhost", "password")
    student4.set("topic_needed", "mathematics")
    student4.set("knowledge", 0.4)
    await student4.start(auto_register=True)
    student_agents.append(student4)

    student5 = StudentAgent("student5@localhost", "password")
    student5.set("topic_needed", "physics")
    student5.set("knowledge", 0.1)
    await student5.start(auto_register=True)
    student_agents.append(student5)

    print(f"System ready. {len(student_agents)} students are starting the learning process.")

    # --- (Waiting for students is the same) ---
    wait_tasks = [spade.wait_until_finished(s) for s in student_agents]
    await asyncio.gather(*wait_tasks)

    print("All students have finished learning. Shutting down the system...")

    # --- (Stopping agents is the same) ---
    for agent in agents:
        await agent.stop()
    
    for student in student_agents:
        await student.stop()

    # --- THE FIX: Wait 1 second for monitor to print its report ---
    await asyncio.sleep(5)

    print("System shut down.")


if __name__ == "__main__":
    spade.run(main())