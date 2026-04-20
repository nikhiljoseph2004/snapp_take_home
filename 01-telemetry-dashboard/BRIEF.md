# Task 1: Real-Time Telemetry Dashboard

## Context

You're joining a marine robotics team. Our autonomous robotic fish ("AquaBots") collect oceanographic data (temperature, depth, salinity, GPS position) while swimming survey patterns, and transmit telemetry over MQTT. Operators need a live dashboard to monitor the fleet.

Your job is to build a prototype of this telemetry dashboard.

## What We Provide

- `virtual_fish.py` — A Python simulator that publishes realistic mock telemetry to an MQTT broker every 2 seconds. You can run multiple instances to simulate multiple robots.
- `requirements.txt` — Dependencies for the simulator

You will need a local MQTT broker. The easiest option:
```bash
# Option A: Docker (recommended)
docker run -d --name mosquitto -p 1883:1883 eclipse-mosquitto:2 mosquitto -c /mosquitto-no-auth.conf

# Option B: Install Mosquitto locally
# macOS: brew install mosquitto && mosquitto
# Ubuntu: sudo apt install mosquitto && mosquitto
```

## What You Build

### Core Requirements

1. **MQTT Subscriber** — A backend service that connects to the MQTT broker and subscribes to `aquabot/telemetry/#` to receive messages from all robots
2. **Data Storage** — Persist received telemetry so it survives a server restart. SQLite is perfectly fine. If database setup is blocking you, store data in-memory and be prepared to discuss the real implementation.
3. **Live Dashboard** — A web-based GUI that displays:
   - A **time-series chart** showing at least 2 sensor readings over time (e.g., water temperature and depth)
   - The robot's **current GPS position on a map**
   - A **status indicator** showing battery level and whether data is flowing
4. **Live Updates** — The dashboard should update in real-time without requiring a page refresh (WebSocket, Server-Sent Events, or short polling)

### Stretch Goals

- Display multiple fish on the same dashboard simultaneously (run 2–3 `virtual_fish.py` instances)
- Historical data playback — select a time range and replay past telemetry
- Visual indication when a robot stops sending data (connection loss detection)
- Docker Compose setup for the full stack (broker + your backend + frontend)

## Technology

Use whatever languages and frameworks you're most productive in. Some popular stacks that would work well:
- Python (Flask/FastAPI) + any frontend (React, Vue, vanilla JS)
- Node.js (Express) + any frontend
- Charting: Plotly, Chart.js, D3, or anything you like
- Maps: Leaflet.js + OpenStreetMap tiles (free, no API key needed)

## Deliverables

- Source code in a git repository with meaningful commits
- A README covering: setup instructions, architecture decisions, and what you'd improve with more time
- Be prepared to demo it live and walk through the code

## Discussion Topics (for the in-person walkthrough)

We'll talk about these — you don't need to implement them, but think about them:
- How would your architecture change if there were 100 simultaneous robots?
- How would you deploy this stack using Docker / docker-compose?
- How should the dashboard handle it when a robot loses connectivity for 5 minutes and then reconnects with a burst of buffered data?
- Where in the pipeline would you add data validation, and what would you check?
