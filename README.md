# AUS-Lab

**Autonomous UAV Swarm Laboratory**

An experimental framework exploring LLM-driven cognitive control of UAV swarms through agentic reasoning, translation layers, and hardware-in-the-loop simulation.

## Overview

AUS-Lab investigates how Large Language Models can serve as the cognitive layer in autonomous UAV networks—interpreting high-level natural language commands and translating them into distributed swarm actions. The system demonstrates task decomposition, adaptive coordination, and autonomous correction in multi-agent systems.

## Architecture

```
Input → Agentic System (LLM) → Translation Layer (Actions) → Swarm Simulation
  ↑                                                                  ↓
  └──────────── Translation Layer (Environment) ←──────────────────┘
```

**Core Components:**

- **Agentic System**: LLM-powered reasoning layer for task interpretation and swarm coordination
- **Translation Layers**: Bidirectional interface converting between natural language/abstract goals and simulation API commands
- **Swarm Simulation**: 3D physics-based UAV environment (PyBullet/Webots)
- **Frontend**: Real-time visualization and monitoring dashboard

## Key Features

- Natural language task specification and decomposition
- Autonomous multi-agent coordination and role assignment
- Real-time environmental feedback and adaptive replanning
- Modular interface between reasoning, translation, and simulation layers
- Hardware-in-the-loop (HIL) integration capabilities

## Research Phases

**Phase 1 — Research & Planning**
- Theoretical foundations for agentic UAV swarms
- Survey of LLM-guided robotics and swarm coordination methods
- Modular interface design

**Phase 2 — Experimental Iteration**
- 3D simulation implementation (PyBullet + gym-pybullet-drones)
- Agentic translation layer prototyping
- HIL testing with hardware nodes
- Emergent behavior analysis

## Core Innovations

1. **Agentic Cognitive Layer**: LLM-driven reasoning replacing rule-based swarm controllers
2. **Bi-Directional Translation**: Structured schema for environment-action communication
3. **Hybrid Control Loop**: Integration of control theory with LLM reasoning
4. **Long-Running Autonomy**: Sustained multi-mission task reassignment and failure recovery

## References

Key research informing this work:

- Tian et al. (2025) - "UAVs Meet LLMs" (arXiv:2501.02341)
- Chen et al. (2023) - "Distributed Task Allocation for Multiple UAVs" (*Drones* 8(12):766)
- Jiao et al. (2023) - "Swarm-GPT" (arXiv:2312.01059)
- Xie et al. (2025) - "FANET-Sim" (ACM CNSSE '25)

## Project Structure

```
agentic/          # Agentic system and LLM reasoning components
simulation/       # UAV swarm simulation environment
translation/      # Action and environment translation layers
frontend/         # Visualization dashboard
```

## Goals

- Demonstrate LLM-commanded UAV swarm coordination through natural language
- Prove autonomous task reassignment and adaptive behavior
- Establish framework for agentic multi-agent systems

---

*Research exploring the intersection of Swarm Structures, Hardware-in-the-Loop, Agentic Systems, and Large Language Models.*
