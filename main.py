# project/main.py
# Main system integration and launch file.
# Manages the startup, execution, and shutdown of all agents.

import asyncio
import spade
import random
from spade.behaviour import PeriodicBehaviour

# Import agent classes from other files
from agents.student_agent import StudentAgent
from agents.tutor_agent import TutorAgent
from agents.resource_agent import ResourceAgent


# from agents.monitor_agent import MonitorAgent # To be provided by Łukasz

# --- Dynamic Environment (Kuba's Task) ---
class DynamicEnvironmentBehav(PeriodicBehaviour):
    """
    This behaviour simulates a dynamic environment.
    Every 30 seconds, it randomly changes a tutor's availability.
    """

    async def run(self):
        # Select a random tutor from the list provided to the agent
        tutor_to_change = random.choice(self.agent.tutors)
        # Randomly set their new availability
        new_availability = random.choice([True, False])
        tutor_to_change.is_available = new_availability

        # Log the change to the console
        print(f"[Environment]: Tutor {tutor_to_change.name}'s availability changed to: {new_availability}")


async def main():
    print("Starting the multi-agent system...")

    # A list to keep track of all agents for a graceful shutdown
    agents = []

    # 1. Łukasz's Agents (Communication and Resources)
    resource_mgr = ResourceAgent("resource_manager@localhost", "password")
    await resource_mgr.start(auto_register=True)
    agents.append(resource_mgr)

    # monitor = MonitorAgent("monitor@localhost", "password")
    # await monitor.start(auto_register=True)
    # agents.append(monitor)

    # 2. Kuba's Agents (Tutor Logic)
    tutor1 = TutorAgent("tutor1@localhost", "password")
    tutor1.set("expertise", ["mathematics", "physics"])  # Setting the profile
    await tutor1.start(auto_register=True)
    agents.append(tutor1)

    tutor2 = TutorAgent("tutor2@localhost", "password")
    tutor2.set("expertise", ["physics"])  # This tutor only knows physics
    await tutor2.start(auto_register=True)
    agents.append(tutor2)

    # 3. Adding Environment Dynamics (Kuba's Task)
    environment_agent = spade.agent.Agent("environment@localhost", "password")
    environment_agent.tutors = [tutor1, tutor2]  # Give it access to the tutors
    await environment_agent.start(auto_register=True)

    # Run the behaviour every 30 seconds
    env_behav = DynamicEnvironmentBehav(period=30)
    environment_agent.add_behaviour(env_behav)
    agents.append(environment_agent)

    # 4. Kuba's Agent (Student Logic)
    print("Server agents started. Waiting 5s before launching student...")
    await asyncio.sleep(5)

    student = StudentAgent("student@localhost", "password")
    await student.start(auto_register=True)

    print("System ready. Student is starting the learning process.")

    await spade.wait_until_finished(student)

    print("Student has finished learning. Shutting down the system...")

    for agent in agents:
        await agent.stop()
    await student.stop()

    print("System shut down.")


if __name__ == "__main__":
    spade.run(main())