#!/usr/bin/env python3
"""
AquaBot Robot Simulator with Degraded Communication Channel

Simulates a marine robot that receives missions over an unreliable
WebSocket connection. Includes configurable channel degradation:
latency, packet loss, corruption, and link blackouts.
"""

import asyncio
import json
import math
import random
import time
import argparse
import urllib.parse
from datetime import datetime, timezone
from typing import Optional
import websockets
from websockets.server import WebSocketServerProtocol

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def log_channel(msg: str):
    print(f"{Colors.OKCYAN}[CHANNEL]{Colors.ENDC} {msg}")


def log_robot(msg: str):
    print(f"{Colors.OKGREEN}[ROBOT]{Colors.ENDC} {msg}")


def log_send(msg: str):
    print(f"{Colors.OKBLUE}[SEND]{Colors.ENDC} {msg}")


def log_recv(msg: str):
    print(f"{Colors.HEADER}[RECV]{Colors.ENDC} {msg}")


def log_error(msg: str):
    print(f"{Colors.FAIL}[ERROR]{Colors.ENDC} {msg}")


def log_warning(msg: str):
    print(f"{Colors.WARNING}[WARNING]{Colors.ENDC} {msg}")


# Task durations in seconds
TASK_DURATIONS = {
    "sample_water": 8.0,
    "take_photo": 3.0,
    "measure_depth": 5.0,
    "collect_sediment": 12.0,
}

ROBOT_SPEED_KNOTS = 1.5  # Approximate survey speed
KNOTS_TO_METERS_PER_SEC = 0.514444
EARTH_RADIUS_METERS = 6371000


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS coordinates in meters."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_METERS * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing from point 1 to point 2 in degrees (0-360)."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    bearing_rad = math.atan2(x, y)
    bearing_deg = math.degrees(bearing_rad)
    return (bearing_deg + 360) % 360


def move_towards(lat: float, lon: float, bearing: float, distance_m: float) -> tuple[float, float]:
    """Move from (lat, lon) along bearing for distance_m meters."""
    bearing_rad = math.radians(bearing)
    lat_rad = math.radians(lat)

    # Angular distance
    angular_dist = distance_m / EARTH_RADIUS_METERS

    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(angular_dist) +
        math.cos(lat_rad) * math.sin(angular_dist) * math.cos(bearing_rad)
    )

    new_lon_rad = (math.radians(lon) +
                   math.atan2(math.sin(bearing_rad) * math.sin(angular_dist) * math.cos(lat_rad),
                              math.cos(angular_dist) - math.sin(lat_rad) * math.sin(new_lat_rad)))

    return math.degrees(new_lat_rad), math.degrees(new_lon_rad)


class DegradedChannel:
    """
    Simulates an unreliable communication channel.
    Applies latency, packet loss, corruption, and blackouts to messages.
    """

    def __init__(self, latency_ms: int = 500, drop_rate: float = 0.15,
                 corrupt_rate: float = 0.05, blackout_interval: float = 60.0,
                 blackout_duration: float = 10.0, disabled: bool = False):
        self.latency_ms = latency_ms
        self.drop_rate = drop_rate
        self.corrupt_rate = corrupt_rate
        self.blackout_interval = blackout_interval
        self.blackout_duration = blackout_duration
        self.disabled = disabled

        self.in_blackout = False
        self.last_blackout_start: Optional[float] = None
        self.next_blackout_time = time.time() + self._randomized_interval()

    def _randomized_interval(self) -> float:
        """Return blackout interval with ±30% variance."""
        variance = self.blackout_interval * 0.3
        return self.blackout_interval + random.uniform(-variance, variance)

    def _update_blackout_state(self):
        """Check if we should start or end a blackout."""
        if self.disabled:
            return

        now = time.time()

        if self.in_blackout:
            if now - self.last_blackout_start >= self.blackout_duration:
                self.in_blackout = False
                self.next_blackout_time = now + self._randomized_interval()
                log_channel(f"{Colors.WARNING}=== BLACKOUT ENDED (next in ~{self.next_blackout_time - now:.0f}s) ==={Colors.ENDC}")
        else:
            if now >= self.next_blackout_time:
                self.in_blackout = True
                self.last_blackout_start = now
                log_channel(f"{Colors.FAIL}=== BLACKOUT STARTED (duration: {self.blackout_duration}s) ==={Colors.ENDC}")

    async def apply(self, message: str, direction: str) -> Optional[str]:
        """
        Apply channel degradation to a message.
        Returns the (possibly corrupted) message, or None if dropped.
        """
        if self.disabled:
            await asyncio.sleep(random.uniform(0.001, 0.010))  # Minimal delay
            return message

        self._update_blackout_state()

        # Check for blackout - messages get silently dropped
        if self.in_blackout:
            log_channel(f"[{direction}] Dropped (blackout): {message[:60]}...")
            return None

        # Apply random latency
        delay_ms = random.uniform(0, self.latency_ms)
        await asyncio.sleep(delay_ms / 1000.0)

        # Random drop
        if random.random() < self.drop_rate:
            log_channel(f"[{direction}] Dropped (random): {message[:60]}...")
            return None

        # Corruption
        if random.random() < self.corrupt_rate:
            corrupted = self._corrupt_message(message)
            log_channel(f"[{direction}] Corrupted: {corrupted[:80]}...")
            return corrupted

        return message

    def _corrupt_message(self, message: str) -> str:
        """
        Corrupt a message in one of several ways:
        - Truncate at random point
        - Flip random characters
        - Swap random bytes
        """
        choice = random.choice(["truncate", "flip", "swap"])

        if choice == "truncate" and len(message) > 20:
            truncate_point = random.randint(len(message) // 2, len(message) - 1)
            return message[:truncate_point]

        elif choice == "flip":
            chars = list(message)
            num_flips = max(1, len(chars) // 20)
            for _ in range(num_flips):
                idx = random.randint(0, len(chars) - 1)
                if chars[idx].isalpha():
                    chars[idx] = chr(ord(chars[idx]) ^ 0x01)  # Flip low bit
            return ''.join(chars)

        else:  # swap
            chars = list(message)
            if len(chars) > 2:
                idx1 = random.randint(0, len(chars) - 2)
                chars[idx1], chars[idx1 + 1] = chars[idx1 + 1], chars[idx1]
            return ''.join(chars)


class RobotSimulator:
    """
    Simulates an AquaBot that executes missions and publishes telemetry.
    """

    def __init__(self, fish_id: str, start_lat: float, start_lon: float,
                 channel: DegradedChannel):
        self.fish_id = fish_id
        self.lat = start_lat
        self.lon = start_lon
        self.channel = channel

        self.mission: Optional[list] = None
        self.mission_active = False
        self.current_waypoint_idx = 0
        self.waypoint_status = "idle"  # idle, in_transit, executing_task, completed
        self.current_task_idx = 0
        self.tasks_completed: list[str] = []
        self.battery_pct = 95.0
        self.start_time = time.time()

        self._seq_counter = 0
        self._lock = asyncio.Lock()
        self._task_handle: Optional[asyncio.Task] = None
        self._connected_client: Optional[WebSocketServerProtocol] = None

    def _next_seq(self) -> int:
        self._seq_counter += 1
        return self._seq_counter

    def _make_message(self, msg_type: str, payload: dict) -> dict:
        return {
            "msg_type": msg_type,
            "seq": self._next_seq(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload
        }

    async def send_message(self, websocket: WebSocketServerProtocol, msg_type: str, payload: dict):
        """Send a message through the degraded channel."""
        msg = self._make_message(msg_type, payload)
        json_msg = json.dumps(msg)
        log_send(f"{msg_type}: {json_msg[:100]}...")

        degraded = await self.channel.apply(json_msg, "OUT")
        if degraded:
            try:
                await websocket.send(degraded)
            except Exception as e:
                log_error(f"Failed to send: {e}")

    async def handle_incoming(self, websocket: WebSocketServerProtocol, message: str):
        """Process an incoming message from the client."""
        # Try to parse JSON - if it fails, the message was likely corrupted
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            log_warning(f"Received corrupted/invalid JSON: {message[:80]}...")
            await self.send_message(websocket, "error", {
                "code": "PARSE_ERROR",
                "message": "Message could not be parsed as JSON"
            })
            return

        msg_type = data.get("msg_type")
        payload = data.get("payload", {})

        log_recv(f"{msg_type}: {json.dumps(payload)[:80]}...")

        if msg_type == "ping":
            await self.send_message(websocket, "pong", {
                "uptime_s": int(time.time() - self.start_time)
            })

        elif msg_type == "mission_upload":
            await self.handle_mission_upload(websocket, payload)

        elif msg_type == "mission_abort":
            await self.handle_mission_abort(websocket)

        else:
            await self.send_message(websocket, "error", {
                "code": "UNKNOWN_MSG_TYPE",
                "message": f"Unknown message type: {msg_type}"
            })

    async def handle_mission_upload(self, websocket: WebSocketServerProtocol, payload: dict):
        """Handle a mission upload request."""
        waypoints = payload.get("waypoints", [])

        if not waypoints:
            await self.send_message(websocket, "mission_ack", {
                "status": "rejected",
                "reason": "No waypoints provided"
            })
            return

        # Validate waypoints
        for i, wp in enumerate(waypoints):
            if "id" not in wp or "lat" not in wp or "lon" not in wp:
                await self.send_message(websocket, "mission_ack", {
                    "status": "rejected",
                    "reason": f"Waypoint {i} missing required fields (id, lat, lon)"
                })
                return

        # Accept mission and start execution
        async with self._lock:
            self.mission = waypoints
            self.mission_active = True
            self.current_waypoint_idx = 0
            self.current_task_idx = 0
            self.waypoint_status = "in_transit"
            self.tasks_completed = []

        await self.send_message(websocket, "mission_ack", {
            "status": "accepted",
            "reason": ""
        })

        log_robot(f"Mission accepted with {len(waypoints)} waypoints")

        # Start mission execution
        if self._task_handle:
            self._task_handle.cancel()
        self._task_handle = asyncio.create_task(self._mission_loop(websocket))

    async def handle_mission_abort(self, websocket: WebSocketServerProtocol):
        """Handle mission abort command."""
        async with self._lock:
            self.mission_active = False
            if self._task_handle:
                self._task_handle.cancel()
                self._task_handle = None

        log_robot("Mission aborted by operator")
        await self.send_message(websocket, "mission_ack", {
            "status": "accepted",
            "reason": "Mission aborted"
        })

        # Return to first waypoint
        if self.mission and len(self.mission) > 0:
            first_wp = self.mission[0]
            await self._return_to_base(websocket, first_wp["lat"], first_wp["lon"])

    async def _return_to_base(self, websocket: WebSocketServerProtocol, base_lat: float, base_lon: float):
        """Return to base waypoint after abort."""
        log_robot(f"Returning to base at ({base_lat:.4f}, {base_lon:.4f})")

        while haversine_distance(self.lat, self.lon, base_lat, base_lon) > 10:
            bearing = calculate_bearing(self.lat, self.lon, base_lat, base_lon)
            distance = ROBOT_SPEED_KNOTS * KNOTS_TO_METERS_PER_SEC * 2  # 2 second progress interval
            self.lat, self.lon = move_towards(self.lat, self.lon, bearing, distance)

            await self.send_message(websocket, "progress", {
                "current_wp": "BASE",
                "wp_status": "returning",
                "position": {"lat": round(self.lat, 6), "lon": round(self.lon, 6)},
                "battery_pct": round(self.battery_pct, 1),
                "tasks_completed": self.tasks_completed
            })
            await asyncio.sleep(2)

        log_robot("Arrived at base")

    async def _mission_loop(self, websocket: WebSocketServerProtocol):
        """Main mission execution loop."""
        while self.mission_active and self.current_waypoint_idx < len(self.mission):
            wp = self.mission[self.current_waypoint_idx]
            wp_id = wp["id"]
            target_lat = wp["lat"]
            target_lon = wp["lon"]
            tasks = wp.get("tasks", [])

            log_robot(f"Navigating to waypoint {wp_id} at ({target_lat:.4f}, {target_lon:.4f})")

            # Navigate to waypoint
            self.waypoint_status = "in_transit"
            while self.mission_active:
                dist = haversine_distance(self.lat, self.lon, target_lat, target_lon)
                if dist < 5:  # Within 5 meters
                    break

                bearing = calculate_bearing(self.lat, self.lon, target_lat, target_lon)
                distance = ROBOT_SPEED_KNOTS * KNOTS_TO_METERS_PER_SEC * 2
                self.lat, self.lon = move_towards(self.lat, self.lon, bearing, distance)

                await self._send_progress(websocket, wp_id)
                await asyncio.sleep(2)

            if not self.mission_active:
                break

            log_robot(f"Arrived at waypoint {wp_id}")
            self.waypoint_status = "executing_task"

            # Execute tasks at waypoint
            self.current_task_idx = 0
            for task in tasks:
                if not self.mission_active:
                    break

                if task not in TASK_DURATIONS:
                    log_warning(f"Unknown task: {task}")
                    continue

                log_robot(f"Starting task '{task}' at {wp_id}")
                await asyncio.sleep(TASK_DURATIONS[task])

                if self.mission_active:
                    result = "success" if random.random() > 0.05 else "failure"
                    await self.send_message(websocket, "task_complete", {
                        "waypoint_id": wp_id,
                        "task": task,
                        "result": result
                    })
                    self.tasks_completed.append(f"{wp_id}:{task}")
                    log_robot(f"Task '{task}' completed with result: {result}")

            self.waypoint_status = "completed"
            await self._send_progress(websocket, wp_id)

            self.current_waypoint_idx += 1

        if self.mission_active:
            log_robot("Mission completed successfully")
            await self.send_message(websocket, "mission_complete", {
                "waypoints_visited": self.current_waypoint_idx,
                "tasks_completed": len(self.tasks_completed)
            })
            self.mission_active = False

    async def _send_progress(self, websocket: WebSocketServerProtocol, current_wp_id: str):
        """Send a progress update and drain battery."""
        self.battery_pct = max(0, self.battery_pct - 0.1)

        await self.send_message(websocket, "progress", {
            "current_wp": current_wp_id,
            "wp_status": self.waypoint_status,
            "position": {"lat": round(self.lat, 6), "lon": round(self.lon, 6)},
            "battery_pct": round(self.battery_pct, 1),
            "tasks_completed": self.tasks_completed
        })


async def handle_connection(websocket: WebSocketServerProtocol,
                             args: argparse.Namespace):
    """Handle a new WebSocket connection."""
    # Parse query parameters for per-connection degradation settings
    path = websocket.request.path if hasattr(websocket, 'request') and websocket.request else "/"
    parsed = urllib.parse.urlparse(path)
    params = urllib.parse.parse_qs(parsed.query)

    latency_ms = int(params.get("latency_ms", [args.latency])[0])
    drop_rate = float(params.get("drop_rate", [args.drop_rate])[0])
    corrupt_rate = float(params.get("corrupt_rate", [args.corrupt_rate])[0])
    blackout_interval = float(params.get("blackout_interval", [args.blackout_interval])[0])

    disabled = args.no_degrade

    log_channel(f"New connection from {websocket.remote_address}")
    log_channel(f"Channel config: latency={latency_ms}ms, drop={drop_rate:.0%}, "
                f"corrupt={corrupt_rate:.0%}, blackout_int={blackout_interval}s, "
                f"disabled={disabled}")

    channel = DegradedChannel(
        latency_ms=latency_ms,
        drop_rate=drop_rate,
        corrupt_rate=corrupt_rate,
        blackout_interval=blackout_interval,
        blackout_duration=args.blackout_duration,
        disabled=disabled
    )

    robot = RobotSimulator(
        fish_id=args.fish_id,
        start_lat=args.start_lat,
        start_lon=args.start_lon,
        channel=channel
    )

    try:
        async for message in websocket:
            # Apply inbound channel degradation
            degraded = await channel.apply(message, "IN")
            if degraded is None:
                continue

            await robot.handle_incoming(websocket, degraded)

    except websockets.exceptions.ConnectionClosed:
        log_channel("Connection closed")
    except Exception as e:
        log_error(f"Error in connection handler: {e}")
    finally:
        if robot._task_handle:
            robot._task_handle.cancel()


def main():
    parser = argparse.ArgumentParser(
        description="AquaBot Robot Simulator with Degraded Channel"
    )
    parser.add_argument("--port", type=int, default=8765,
                        help="WebSocket server port (default: 8765)")
    parser.add_argument("--latency", type=int, default=500,
                        help="Max random latency in ms (default: 500)")
    parser.add_argument("--drop-rate", type=float, default=0.15,
                        help="Message drop probability (default: 0.15)")
    parser.add_argument("--corrupt-rate", type=float, default=0.05,
                        help="Message corruption probability (default: 0.05)")
    parser.add_argument("--blackout-interval", type=float, default=60.0,
                        help="Seconds between blackouts (default: 60)")
    parser.add_argument("--blackout-duration", type=float, default=10.0,
                        help="Blackout duration in seconds (default: 10)")
    parser.add_argument("--fish-id", type=str, default="fish-01",
                        help="Robot identifier (default: fish-01)")
    parser.add_argument("--start-lat", type=float, default=32.6881,
                        help="Starting latitude (default: 32.6881)")
    parser.add_argument("--start-lon", type=float, default=-117.1777,
                        help="Starting longitude (default: -117.1777)")
    parser.add_argument("--no-degrade", action="store_true",
                        help="Disable all channel degradation")

    args = parser.parse_args()

    print(f"\n{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}AquaBot Robot Simulator{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"Robot ID: {Colors.OKGREEN}{args.fish_id}{Colors.ENDC}")
    print(f"Starting position: ({args.start_lat}, {args.start_lon})")
    print(f"WebSocket server: ws://localhost:{args.port}")
    print(f"Degradation: {'DISABLED' if args.no_degrade else 'ENABLED'}")

    if not args.no_degrade:
        print(f"  - Latency: 0-{args.latency}ms")
        print(f"  - Drop rate: {args.drop_rate:.0%}")
        print(f"  - Corruption rate: {args.corrupt_rate:.0%}")
        print(f"  - Blackouts: every ~{args.blackout_interval}s for {args.blackout_duration}s")

    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

    async def handler(websocket):
        await handle_connection(websocket, args)

    async def run_server():
        async with websockets.serve(handler, "localhost", args.port):
            print(f"Server running. Press Ctrl+C to stop.\n")
            await asyncio.Future()  # run forever

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
