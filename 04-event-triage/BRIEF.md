# Task 4: Sensor Event Triage System

## Context

Our AquaBots are equipped with cameras and hydrophones (underwater microphones). While on a mission, onboard algorithms detect "events" — things like fish sightings, obstacle encounters, unusual acoustic signatures, or potential marine mammal vocalizations. Each event generates a data packet: some metadata (timestamp, GPS, confidence score, sensor type) and an associated image (a camera frame or a spectrogram of the audio).

After a mission, marine scientists need to review these events, verify the automatic classifications, and flag interesting finds for further analysis. Currently this is done by scrolling through folders of files — it's slow and error-prone.

Your job is to build a web-based "Triage Inbox" that makes this review process fast and organized.

## What We Provide

- `events/` — A folder containing 30 mock detection events, each with:
  - A JSON metadata file (`event_001.json`, etc.)
  - An associated image (`event_001.png`, etc.)
- `generate_events.py` — The script that generated the mock data (for reference)

### Event Metadata Format

```json
{
  "event_id": "event_001",
  "timestamp": "2025-07-15T14:30:00Z",
  "fish_id": "fish-01",
  "gps": {"lat": 32.688, "lon": -117.178},
  "depth_m": 3.2,
  "sensor_type": "camera" | "hydrophone",
  "auto_classification": "fish" | "marine_mammal" | "obstacle" | "unknown",
  "confidence": 0.87,
  "image_path": "event_001.png",
  "notes": ""
}
```

## What You Build

### Core Requirements

1. **Backend** — A server that:
   - Loads and serves the event data
   - Provides API endpoints for listing, filtering, and updating events
   - Persists classification changes (database, flat files, or in-memory with discussion of real storage)

2. **Triage Inbox View** — A web page with:
   - A **scrollable list/grid** of events showing: thumbnail, timestamp, sensor type, auto-classification, confidence score, and review status
   - **Sort** by timestamp, confidence, or sensor type
   - **Filter** by: review status (unreviewed / reviewed), sensor type (camera / hydrophone), auto-classification, confidence threshold

3. **Event Detail View** — Clicking an event opens a detailed view with:
   - Full-size image (camera frame or spectrogram)
   - All metadata displayed clearly
   - GPS location on a small map
   - **Classification controls**: buttons or dropdown to classify as: `Fish`, `Marine Mammal`, `Obstacle`, `Interesting (needs follow-up)`, `False Alarm`
   - A **text field** for the reviewer to add notes
   - Save button that persists the classification and notes

4. **Summary Panel** — Visible on the main view:
   - Count of reviewed vs. unreviewed events
   - Breakdown by classification (e.g., "8 Fish, 3 Mammals, 2 Obstacles, 5 False Alarms, 12 Unreviewed")

### Stretch Goals

- **Keyboard shortcuts** for rapid triage (e.g., `1`=Fish, `2`=Mammal, `3`=Obstacle, `4`=Interesting, `5`=False Alarm, `→`=next event)
- **Bulk classification** — select multiple events and classify them all at once
- **Confidence-based smart sorting** — show low-confidence events first (they need human review most)
- **Map overview** — show all events as pins on a map, colored by classification
- **Export** — download reviewed events as a CSV summary

## Technology

Use whatever you're most comfortable with. Some good options:
- Python (Flask/FastAPI) + any frontend framework
- Node.js (Express) + any frontend
- The images are static PNGs — serve them from disk or embed as base64
- Leaflet.js for any map features

## Deliverables

- Source code in a git repository with meaningful commits
- A README covering: setup instructions, architecture decisions, UX choices you made and why, what you'd improve with more time
- Be prepared to demo and walk through the code

## Discussion Topics (for the in-person walkthrough)

- The AquaBot detects an event but only has a low-bandwidth LoRaWAN connection. How do you get the image back to the server? What would you send first?
- How would you prioritize events for human review if the robot generates hundreds per mission? What metadata would help an auto-triage system?
- If we wanted to use the human classifications to improve the onboard ML model, how would you close that feedback loop?
- How would you handle multiple scientists reviewing the same events simultaneously (conflict resolution)?
