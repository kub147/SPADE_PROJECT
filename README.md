# 🎓 Multi-Agent Tutoring System

A distributed learning platform built with SPADE (Smart Python Agent Development Environment) using XMPP protocol for agent communication.

## 📋 Project Structure
```
project/
├── agents/
│   ├── __init__.py              # Required by Python
│   ├── student_agent.py         # Student agent with FSM (v1 Done - Kuba)
│   ├── tutor_agent.py           # Tutor agent with availability mgmt (v1 Done - Kuba)
│   ├── resource_agent.py        # Resource provider (To take over - Łukasz)
│   ├── monitor_agent.py         # Monitoring & metrics (To-Do - Łukasz)
│   └── peer_agent.py            # Peer learning agent (Optional)
│
├── docs/
│   └── report.md                # Final documentation (To-Do - Bruno)
│
├── visualization/
│   └── dashboard.py             # Web dashboard (To-Do - Bruno)
│
├── venv/                        # Local environment (ignored by Git)
│
├── main.py                      # Main orchestrator (v1 Done - Kuba)
└── requirements.txt             # Dependencies (Generated - Kuba)
```

## 🚀 Quick Start

### Step 1: Create Virtual Environment
```bash
# Create the environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# or (Windows CMD)
# venv\Scripts\activate
```

### Step 2: Install Dependencies
```bash
# Install required packages
pip install -r requirements.txt
```

### Step 3: Run XMPP Server (Terminal 1)
```bash
# Start the SPADE server
spade run
```

**⚠️ Keep this terminal running!** You should see: `SUCCESS: Server started...`

### Step 4: Run Agents (Terminal 2)
```bash
# Launch the simulation
python main.py
```

You should now see the full simulation log with agent interactions.

## 🏗️ Architecture

### Agent Roles

#### 🎓 Student Agent (`student_agent.py`)
- **Purpose**: Manages the learning process using a Finite State Machine (FSM)
- **Features**:
  - Knowledge profile tracking (0.0 - 1.0 scale)
  - Learning goal setting
  - Resource requesting
  - Contract Net Protocol client for tutor selection
- **Status**: ✅ v1 Done (Kuba)

#### 👨‍🏫 Tutor Agent (`tutor_agent.py`)
- **Purpose**: Provides tutoring services based on expertise
- **Features**:
  - Expertise profile (subject-specific)
  - Availability management
  - Contract Net Protocol server
  - Session workload handling
- **Status**: ✅ v1 Done (Kuba)

#### 📚 Resource Agent (`resource_agent.py`)
- **Purpose**: Provides learning resources and recommendations
- **Features**:
  - Resource database (JSON-based)
  - Subject-based resource lookup
  - Learning style recommendations
- **Status**: 🔄 To take over (Łukasz)

#### 📊 Monitor Agent (`monitor_agent.py`)
- **Purpose**: Collects metrics and system statistics
- **Features**:
  - Event logging
  - Performance metrics calculation
  - Workload tracking
- **Status**: 📝 To-Do (Łukasz)

#### 👥 Peer Agent (`peer_agent.py`)
- **Purpose**: Facilitates peer-to-peer learning
- **Status**: 🔮 Optional

### 🔄 Communication Flow
```
1. START
   └─> StudentAgent initializes (FSM State: START)

2. RESOURCE REQUEST
   └─> Student → Resource Agent (ResourceProtocol)
       └─> Body: "mathematics"

3. RESOURCE RESPONSE
   └─> Resource → Student (inform)
       └─> Body: "https://resource-link.com" or "ERROR_NOT_FOUND"

4. STUDENT ADAPTATION
   └─> Student studies resource (+0.4 knowledge)
   └─> Evaluates if goal is met
   └─> Decides to find tutor if needed

5. CONTRACT NET (CFP)
   └─> Student → All Tutors (fipa-contract-net, cfp)
       └─> Body: "mathematics"

6. PROPOSALS
   └─> Tutor 1 (available, knows math) → propose
       └─> Body: {"wait_time": 5, "expertise_level": 0.9}
   └─> Tutor 2 (unavailable) → ignores

7. SELECTION
   └─> Student evaluates proposals (5s window)
   └─> Selects best offer (lowest wait_time)

8. ACCEPT/REJECT
   └─> Student → Winner (accept-proposal)
   └─> Student → Others (reject-proposal)

9. SESSION
   └─> Tutor sets is_available = False
   └─> Tutor → Student (confirm)
   └─> Session simulation
   └─> Student updates knowledge → 1.0

10. END
    └─> Student FSM State: FINISH
```

## 📡 API Contract

### Message Formats

| From | To | Protocol | Performative | Body |
|------|----|---------| -------------|------|
| Student | Resource | `ResourceProtocol` | `request` | `"mathematics"` |
| Resource | Student | - | `inform` | `"https://link.com"` or `"ERROR_NOT_FOUND"` |
| Student | Tutors | `fipa-contract-net` | `cfp` | `"mathematics"` |
| Tutor | Student | `fipa-contract-net` | `propose` | `{"wait_time": 5, "expertise_level": 0.9}` |
| Student | Tutor (Winner) | `fipa-contract-net` | `accept-proposal` | `""` |
| Student | Tutor (Loser) | `fipa-contract-net` | `reject-proposal` | `""` |
| Tutor | Student | - | `inform` | `"OK, starting session."` |
| Any Agent | Monitor | `MonitoringProtocol` | `inform` | `"Log message"` |

### Protocol Guidelines

- Use `msg.make_reply()` to create response messages
- Follow FIPA standards for Contract Net Protocol
- Always include appropriate performatives
- Validate message body formats before processing

## 👥 Team Tasks

### ✅ Completed (Kuba)

- [x] StudentAgent with FSM and CNP client logic
- [x] TutorAgent with profile and workload management
- [x] ResourceAgent v1 (basic implementation)
- [x] Main orchestrator with dynamic environment
- [x] Requirements and project structure

### 🔄 In Progress

#### Łukasz - Communication & Metrics

- [ ] **Take over** `resource_agent.py`:
  - Expand resource database (load from JSON)
  - Add recommendation logic based on learning_style
  - Implement subject-specific resource filtering

- [ ] **Create** `monitor_agent.py`:
  - Implement MonitoringProtocol listener
  - Store logs in structured format (dict/list)
  - Calculate system metrics

- [ ] **Add Metrics Integration**:
  - Modify Student & Tutor agents to send events to Monitor
  - Track: CFP sent, sessions started, knowledge gained
  - Calculate: tutor workload, time to resolution

#### Bruno - Visualization & Documentation

- [ ] **Create** `visualization/dashboard.py`:
  - Build web dashboard (Flask or Dash)
  - Connect as SPADE agent to request stats from MonitorAgent
  - Display live metrics and system status

- [ ] **Write** `docs/report.md`:
  - Document system architecture
  - Describe agent behaviors and protocols
  - Include metrics and test results

- [ ] **Optional**: Implement `peer_agent.py` if time allows

## 📊 Metrics & Monitoring

The MonitorAgent will track the following metrics:

- **Tutor Workload**: Number of active sessions per tutor
- **Time to Resolution**: Duration from CFP to session start
- **Success Rate**: Percentage of successful tutor matches
- **Knowledge Gain**: Average knowledge improvement per student
- **Resource Usage**: Most frequently requested resources

## 🛠️ Technologies

- **SPADE**: Smart Python Agent Development Environment
- **XMPP**: Extensible Messaging and Presence Protocol
- **Python 3.x**: Core programming language
- **FSM**: Finite State Machine for agent behavior
- **FIPA**: Foundation for Intelligent Physical Agents standards


## 👨‍💻 Contributors

- **Kuba**: Core agent development (Student, Tutor, Resource v1, Main)
- **Łukasz**: Communication protocols & monitoring system
- **Bruno**: Visualization & documentation