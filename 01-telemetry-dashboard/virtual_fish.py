#!/usr/bin/env python3
"""
Virtual Fish Simulator - AquaBot Telemetry Generator

Publishes realistic mock telemetry data to an MQTT broker simulating an
autonomous underwater robot collecting oceanographic data.
"""

import argparse
import json
import math
import random
import signal
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


class VirtualFish:
    """Simulates an autonomous underwater robot with realistic sensor data."""

    # GPS offset constants (approximate degrees for ~200m at San Diego latitude)
    # 1 degree latitude ≈ 111 km, so 200m ≈ 0.0018 degrees
    LAT_OFFSET_SCALE = 0.0018
    # 1 degree longitude ≈ 93.4 km at 32.7°N, so 200m ≈ 0.0021 degrees
    LON_OFFSET_SCALE = 0.0021

    def __init__(
        self,
        fish_id: str,
        broker: str,
        port: int,
        center_lat: float,
        center_lon: float,
        fast_mode: bool = False,
    ):
        self.fish_id = fish_id
        self.broker = broker
        self.port = port
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.fast_mode = fast_mode

        # Timing
        self.publish_interval = 0.5 if fast_mode else 2.0

        # Battery starts at 95%, drains ~0.05% per message
        self.battery = 95.0
        self.battery_drain_rate = 0.05

        # Previous position for heading calculation
        self.prev_lat = None
        self.prev_lon = None
        self.heading = 0.0

        # Simulation time tracking
        self.start_time = time.time()
        self.message_count = 0

        # Initialize MQTT client using v2 API
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=f"virtual_fish_{fish_id}",
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        # Graceful shutdown flag
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n[{self.fish_id}] Received signal {signum}, shutting down...")
        self.running = False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for when the client connects to the broker."""
        if rc == 0:
            print(f"[{self.fish_id}] Connected to MQTT broker at {self.broker}:{self.port}")
        else:
            print(f"[{self.fish_id}] Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback for when the client disconnects from the broker."""
        print(f"[{self.fish_id}] Disconnected from broker (rc={rc})")

    def _calculate_lissajous_position(self, t: float) -> tuple[float, float]:
        """
        Calculate position using Lissajous curve for figure-8 pattern.
        
        The pattern completes a loop every ~5 minutes (300 seconds).
        Using frequency ratio 3:2 creates a pleasing figure-8.
        
        Args:
            t: Time in seconds since start
            
        Returns:
            Tuple of (latitude_offset, longitude_offset) in degrees
        """
        # Period for one complete loop: ~300 seconds (5 minutes)
        period = 300.0
        omega = 2 * math.pi / period

        # Lissajous parameters for figure-8 pattern
        # freq_x : freq_y = 2 : 3 creates a nice figure-8
        freq_x = 2
        freq_y = 3

        # Phase shift for smoother motion
        phase_x = 0
        phase_y = math.pi / 2

        # Calculate normalized position (-1 to 1)
        x = math.sin(freq_x * omega * t + phase_x)
        y = math.sin(freq_y * omega * t + phase_y)

        # Convert to degree offsets (200m radius)
        lat_offset = y * self.LAT_OFFSET_SCALE
        lon_offset = x * self.LON_OFFSET_SCALE

        return lat_offset, lon_offset

    def _calculate_depth(self, t: float) -> float:
        """
        Calculate depth with sinusoidal dive cycles.
        
        Dives from 0.5m (surface) to 8m (deep) with ~60 second period.
        
        Args:
            t: Time in seconds since start
            
        Returns:
            Depth in meters
        """
        period = 60.0  # 60 second dive cycle
        omega = 2 * math.pi / period

        # Sinusoidal oscillation between min and max depth
        min_depth = 0.5
        max_depth = 8.0
        amplitude = (max_depth - min_depth) / 2
        mean_depth = (max_depth + min_depth) / 2

        depth = mean_depth + amplitude * math.sin(omega * t)

        # Add small noise
        depth += random.gauss(0, 0.05)

        return max(min_depth, min(max_depth, depth))

    def _calculate_temperature(self, depth: float) -> float:
        """
        Calculate water temperature based on depth with thermocline.
        
        Surface water (~0.5m): ~20°C
        Deep water (~8m): ~14°C
        Thermocline region: smooth transition
        
        Args:
            depth: Current depth in meters
            
        Returns:
            Temperature in Celsius
        """
        # Temperature-depth relationship
        surface_temp = 20.0
        deep_temp = 14.0
        thermocline_start = 2.0  # meters
        thermocline_end = 5.0    # meters

        if depth <= thermocline_start:
            temp = surface_temp
        elif depth >= thermocline_end:
            temp = deep_temp
        else:
            # Smooth transition through thermocline
            ratio = (depth - thermocline_start) / (thermocline_end - thermocline_start)
            temp = surface_temp + (deep_temp - surface_temp) * ratio

        # Add small noise
        temp += random.gauss(0, 0.1)

        return temp

    def _calculate_salinity(self) -> float:
        """
        Calculate salinity with small natural variations.
        
        Returns:
            Salinity in practical salinity units (ppt)
        """
        base_salinity = 33.5
        noise = random.gauss(0, 0.3)
        return base_salinity + noise

    def _calculate_speed(self, dt: float) -> float:
        """
        Calculate speed based on movement pattern.
        
        Typical speed: 1-2 knots with noise.
        
        Args:
            dt: Time step in seconds
            
        Returns:
            Speed in knots
        """
        # Base speed around 1.5 knots with variation
        base_speed = 1.5
        noise = random.gauss(0, 0.2)
        speed = max(0.5, min(3.0, base_speed + noise))
        return speed

    def _calculate_heading(self, lat: float, lon: float) -> float:
        """
        Calculate heading based on actual movement direction.
        
        Args:
            lat: Current latitude
            lon: Current longitude
            
        Returns:
            Heading in degrees (0-360, where 0 is North)
        """
        if self.prev_lat is None or self.prev_lon is None:
            self.prev_lat = lat
            self.prev_lon = lon
            return 0.0

        # Calculate bearing from previous position
        dlat = lat - self.prev_lat
        dlon = lon - self.prev_lon

        # Convert to approximate meters for bearing calculation
        # This is a simplified calculation valid for small distances
        dy = dlat * 111000  # meters per degree latitude
        dx = dlon * 93400   # meters per degree longitude at ~32.7°N

        if abs(dx) < 0.001 and abs(dy) < 0.001:
            # No significant movement, keep previous heading
            return self.heading

        # Calculate bearing (0° is North, 90° is East)
        bearing = math.degrees(math.atan2(dx, dy))
        if bearing < 0:
            bearing += 360

        # Smooth heading transition (avoid jumps)
        heading_diff = bearing - self.heading
        while heading_diff > 180:
            heading_diff -= 360
        while heading_diff < -180:
            heading_diff += 360

        self.heading = (self.heading + heading_diff * 0.3) % 360

        self.prev_lat = lat
        self.prev_lon = lon

        return self.heading

    def _generate_telemetry(self) -> dict:
        """Generate a complete telemetry payload."""
        t = time.time() - self.start_time

        # GPS position
        lat_offset, lon_offset = self._calculate_lissajous_position(t)
        lat = self.center_lat + lat_offset
        lon = self.center_lon + lon_offset

        # Depth and derived temperature
        depth = self._calculate_depth(t)
        temperature = self._calculate_temperature(depth)

        # Other sensors
        salinity = self._calculate_salinity()
        speed = self._calculate_speed(self.publish_interval)
        heading = self._calculate_heading(lat, lon)

        # Battery drain
        self.battery = max(0.0, self.battery - self.battery_drain_rate)

        self.message_count += 1

        return {
            "fish_id": self.fish_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "position": {
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
            },
            "depth_m": round(depth, 2),
            "temperature_c": round(temperature, 2),
            "salinity_psu": round(salinity, 2),
            "speed_knots": round(speed, 2),
            "heading_deg": round(heading, 1),
            "battery_pct": round(self.battery, 1),
            "sequence": self.message_count,
        }

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[{self.fish_id}] Failed to connect: {e}")
            return False

    def run(self):
        """Main loop: generate and publish telemetry."""
        if not self.connect():
            return

        topic = f"aquabot/telemetry/{self.fish_id}"

        print(f"[{self.fish_id}] Starting telemetry broadcast...")
        print(f"[{self.fish_id}] Publishing to {topic} every {self.publish_interval}s")
        print(f"[{self.fish_id}] Press Ctrl+C to stop\n")

        try:
            while self.running and self.battery > 0:
                telemetry = self._generate_telemetry()
                payload = json.dumps(telemetry, indent=2)

                # Publish to MQTT
                result = self.client.publish(topic, payload, qos=1)

                # Pretty print to stdout
                print(f"[{self.fish_id}] Published to {topic}:")
                print(payload)
                print()

                # Wait for next interval
                time.sleep(self.publish_interval)

        except Exception as e:
            print(f"\n[{self.fish_id}] Error: {e}")
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean up and disconnect."""
        print(f"[{self.fish_id}] Shutting down...")
        self.client.loop_stop()
        self.client.disconnect()
        print(f"[{self.fish_id}] Total messages sent: {self.message_count}")
        print(f"[{self.fish_id}] Final battery: {self.battery:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Virtual Fish - AquaBot Telemetry Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Default fish-01
  %(prog)s --fish-id fish-02                  # Second robot
  %(prog)s --broker mqtt.example.com          # Remote broker
  %(prog)s --fast                             # Fast mode (0.5s intervals)
  %(prog)s --center-lat 33.0 --center-lon -118.0  # Different location
        """,
    )

    parser.add_argument(
        "--broker",
        default="localhost",
        help="MQTT broker address (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)",
    )
    parser.add_argument(
        "--fish-id",
        default="fish-01",
        help="Unique identifier for this fish (default: fish-01)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast mode: publish every 0.5s instead of 2s",
    )
    parser.add_argument(
        "--center-lat",
        type=float,
        default=32.6881,
        help="Center latitude for patrol pattern (default: 32.6881, San Diego Bay)",
    )
    parser.add_argument(
        "--center-lon",
        type=float,
        default=-117.1777,
        help="Center longitude for patrol pattern (default: -117.1777, San Diego Bay)",
    )

    args = parser.parse_args()

    fish = VirtualFish(
        fish_id=args.fish_id,
        broker=args.broker,
        port=args.port,
        center_lat=args.center_lat,
        center_lon=args.center_lon,
        fast_mode=args.fast,
    )

    fish.run()


if __name__ == "__main__":
    main()
