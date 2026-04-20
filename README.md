# Software Intern — Take-Home Assignment

Welcome! We're a marine robotics startup building autonomous robotic fish ("AquaBots") and unmanned surface vehicles (USVs) for oceanographic data collection. Our systems combine embedded hardware, IoT communication (MQTT, LoRaWAN, 4G), sensor data pipelines, and web-based operator tools.

This repository contains **four self-contained project options**. You will choose **one** to complete as a take-home prototype.

## How This Works

1. **Read through all four project briefs** in the `tasks/` directory
2. **Choose the one** that best matches your interests and strengths
3. **Build a working prototype** — budget approximately **8 hours** of focused work
4. **Bring it to our in-person walkthrough** where you'll demo it and we'll discuss your design decisions together

## The Four Projects

| # | Project | Primary Focus | Key Skills |
|---|---------|--------------|------------|
| 1 | [Real-Time Telemetry Dashboard](tasks/01-telemetry-dashboard/BRIEF.md) | IoT, real-time data, GUI | MQTT, WebSockets, charting, maps |
| 2 | [Water Quality Data Pipeline](tasks/02-water-quality-pipeline/BRIEF.md) | Data processing, visualization | Data cleaning, anomaly detection, REST APIs |
| 3 | [Mission Planner with Comms Protocol](tasks/03-mission-planner/BRIEF.md) | Protocol design, systems thinking | Reliable messaging, state sync, maps |
| 4 | [Sensor Event Triage System](tasks/04-event-triage/BRIEF.md) | Internal tooling, data management | CRUD, filtering, image handling, UX |

Each project brief contains:
- Context and motivation
- What we provide (starter scripts, mock data)
- What you build (core requirements)
- Stretch goals (for if you have extra time or want to show off)
- Discussion topics we'll cover in the walkthrough

## Expectations

**This is a prototype, not production code.** We want to see:

- **Problem-solving approach** — How do you break down a new problem? What do you research?
- **Working software** — It should run and be demo-able, even if rough around the edges
- **Architecture awareness** — Can you articulate why you made your choices and what you'd change for production?
- **Communication** — Your README should explain your thinking clearly

**It's completely fine to:**
- Use any language, framework, or library you're comfortable with (we use Python and TypeScript internally)
- Keep data in-memory if database setup is eating your time — just be ready to discuss the real implementation
- Skip authentication, extensive error handling, or CSS polish
- Use AI tools, Stack Overflow, documentation — whatever you'd use on the job

**Please do:**
- Track your work in a git repository with meaningful commits
- Write a README covering: setup instructions, architecture decisions, and what you'd improve with more time
- Be prepared to run the demo live and walk through the code together

## Setup

Each project's `BRIEF.md` includes specific setup instructions. Generally you'll need:
- Python 3.10+ (for the provided simulator scripts)
- A package manager for your chosen stack (npm, pip/uv, etc.)
- Docker (optional, but helpful for Task 1's MQTT broker)

## Questions?

After reading the briefs, you'll have a 30–60 minute Q&A session with us before you start building. Save your questions for then — asking good questions is part of the process.

Good luck, and have fun with it!
