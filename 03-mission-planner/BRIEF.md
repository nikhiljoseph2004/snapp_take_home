# Task 3: Mission Planner with Robust Communication Protocol

## Context

Our AquaBots operate in marine environments where communication is unreliable. Depending on the deployment, a robot might be connected over 4G (decent bandwidth, variable latency), LoRaWAN (tiny payloads, high latency, half-duplex), or even acoustic modems (extremely slow, error-prone). An operator on shore needs to upload missions (sequences of waypoints with tasks) to robots and monitor their progress — all over these degraded links.

Your job is to design a communication protocol and build a mission planner that works reliably even when messages get dropped, delayed, corrupted, or arrive out of order.

## What We Provide

- `robot_sim.py` — A simulated robot that receives missions and "executes" them by moving through waypoints over time. It publishes telemetry back to the base station. Communication goes through a built-in degraded channel.
- `requirements.txt` — Dependencies for the simulator

The simulator exposes a WebSocket server. Your mission planner connects to it as a client. **But the channel is unreliable** — the simulator will:
- Add random latency (0–`latency_ms` ms per message, configurable)
- Drop messages randomly (default 15% drop rate, configurable)
- Occasionally corrupt messages (flip bits, truncate, or swap characters, default 5%)
- Simulate link blackouts (connection appears alive but no messages get through for 5–15 seconds)

You can configure degradation via query parameters when connecting:
```
ws://localhost:8765?latency_ms=1000&drop_rate=0.2&corrupt_rate=0.05&blackout_interval=60
```

### Simulator Message Format

The simulator communicates via JSON messages with this envelope:
```json
{
  "msg_type": "...",
  "seq": 123,
  "timestamp": "2025-07-15T14:30:00.000Z",
  "payload": { ... }
}
```

**Messages the robot understands (you send these):**

| Message Type | Payload | Description |
|--------------|---------|-------------|
| `mission_upload` | `{"waypoints": [...]}` | Upload a mission with waypoints and tasks |
| `mission_abort` | `{}` | Abort current mission, robot returns to first waypoint |
| `ping` | `{}` | Request a pong response for RTT measurement |

**Messages the robot sends (you receive these):**

| Message Type | Payload | Description |
|--------------|---------|-------------|
| `mission_ack` | `{"status": "accepted"\|"rejected", "reason": "..."}` | Response to mission upload |
| `progress` | `{"current_wp": "...", "wp_status": "...", "position": {...}, "battery_pct": 85.0, "tasks_completed": [...]}` | Regular status update every 2s |
| `task_complete` | `{"waypoint_id": "...", "task": "...", "result": "success"\|"failure"}` | Task finished notification |
| `mission_complete` | `{"waypoints_visited": 5, "tasks_completed": 8}` | All waypoints done |
| `pong` | `{"uptime_s": 1234}` | Response to ping |
| `error` | `{"code": "...", "message": "..."}` | Error notification |

**Waypoint object format:**
```json
{
  "id": "wp-1",
  "lat": 32.69,
  "lon": -117.18,
  "tasks": ["sample_water", "take_photo"]
}
```

**Available waypoint tasks:**

| Task | Duration | Description |
|------|----------|-------------|
| `sample_water` | ~8s | Collect water quality sample |
| `take_photo` | ~3s | Capture image at location |
| `measure_depth` | ~5s | Sonar depth measurement |
| `collect_sediment` | ~12s | Grab sediment sample from seafloor |

## What You Build

### Core Requirements

1. **Communication Protocol** — Design and implement a reliable messaging layer on top of the unreliable WebSocket channel:
   - **Message acknowledgment** — know when your mission was received
   - **Retry logic** — resend messages that weren't acknowledged within a timeout
   - **Sequence numbering** — detect and handle out-of-order or duplicate messages
   - **Corruption detection** — identify and discard garbled messages (hint: checksums)

2. **Mission Planner UI** — A web-based interface with:
   - An interactive **map** (Leaflet + OpenStreetMap) for placing waypoints by clicking
   - **Task assignment** — attach one or more tasks to each waypoint from a dropdown/menu
   - **"Upload Mission"** button that sends the mission to the robot through the degraded channel
   - **Mission progress display** — show the robot's real-time position on the map and which waypoints are completed (✓), in-progress (⟳), or pending (○)

3. **Connection Status** — Visual indication of link health:
   - Show when messages are being dropped or delayed
   - Indicate when the link appears to be in a blackout
   - Display round-trip time if you implement ping/pong

### Stretch Goals

- **Mid-mission modification** — add or remove waypoints while the robot is executing
- **Multi-robot support** — connect to multiple simulator instances, each on a different port
- **Compact message encoding** — implement a binary protocol option and compare bandwidth usage to JSON
- **Message integrity** — add checksums (CRC32, hash) to detect corruption before parsing
- **"Return to base"** emergency command with guaranteed delivery (retry until confirmed)
- **Bandwidth estimation** — show estimated bytes/second being used

## Technology

Use whatever you're comfortable with. The simulator uses WebSockets, so your client needs WebSocket support. Some options:

- **Frontend:** React, Vue, vanilla JS + Leaflet.js for maps
- You can build a backend relay or connect directly from the browser
- The protocol layer is the interesting part — implement it however makes sense

## Simulator Usage

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the simulator:
```bash
# Default settings (moderate degradation)
python robot_sim.py

# High degradation (stress test your protocol)
python robot_sim.py --latency 2000 --drop-rate 0.25 --corrupt-rate 0.1

# No degradation (for testing UI features)
python robot_sim.py --no-degrade

# Multiple robots on different ports
python robot_sim.py --port 8765 --fish-id fish-01 &
python robot_sim.py --port 8766 --fish-id fish-02 --start-lat 32.70 --start-lon -117.19 &
```

## Deliverables

- Source code in a git repo with meaningful commits
- A **README** that includes:
  - Setup instructions
  - **Protocol documentation** — describe your message types, acknowledgment scheme, and retry logic (a simple diagram is great but not required)
  - Architecture decisions and tradeoffs
  - What you'd improve with more time
- Be prepared to demo with the channel degradation cranked up

## Discussion Topics (for the in-person walkthrough)

- Walk me through your protocol: what message types did you add? How do you handle a lost ACK — do you resend the mission, and what happens if the robot gets it twice?
- How would your protocol change for LoRaWAN where each message can only be ~50 bytes and you can only send once every 30 seconds?
- What happens if the robot receives a corrupted mission and starts executing garbage waypoints? How do you prevent that?
- How would you add authentication to prevent someone from sending fake missions to our robots?
- What's the difference between at-most-once, at-least-once, and exactly-once delivery? Which does your protocol provide?

---

**Timebox: 8 hours** — Focus on getting the protocol working reliably first, then add UI polish if time permits.
