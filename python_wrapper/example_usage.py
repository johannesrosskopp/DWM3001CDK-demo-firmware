#!/usr/bin/env python3
"""
DWM3001CDK Multi-Device Positioning Example

This script manages multiple DWM3001CDK devices to create a positioning system:
- One tag (initiator) that moves around
- Two beacons (responders) at fixed positions
- Computes tag position in 2D coordinate system
"""

import threading
import time
import argparse
import math
import subprocess
import json
import logging
from typing import Optional, Tuple

# Configuration Parameters
BEACON1_POSITION = (0.0, 0.0)     # Beacon 1 at origin
BEACON2_POSITION = (2.0, 0.0)     # Beacon 2 at (1m, 0m)
REPORT_INTERVAL_SECONDS = 2.0     # Report position every 1 second
DISTANCE_TIMEOUT_SECONDS = 5.0    # Timeout for distance measurements
AVERAGING_WINDOW_SECONDS = 2.0    # Average distances over 2 seconds


class DistanceCollector:
    """Collects distance measurements from a tag device (only tags output distances)"""

    def __init__(self, port: str, averaging_window: float = AVERAGING_WINDOW_SECONDS):
        self.port = port
        self.averaging_window = averaging_window
        self.beacon1_distances = []  # List of (timestamp, distance) tuples
        self.beacon2_distances = []  # List of (timestamp, distance) tuples
        self.running = False
        self.process = None
        self.thread = None

    def start(self):
        """Start the distance collection subprocess for tag"""
        cmd = ['python', 'serial_collector.py', '--port',
               self.port, '--format', 'raw', 'tag']

        logging.debug(f"Starting tag on {self.port}")
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )

        self.running = True
        self.thread = threading.Thread(target=self._read_output)
        self.thread.start()

    def stop(self):
        """Stop the distance collection"""
        self.running = False
        if self.process:
            self.process.terminate()
            self.process.wait()
        if self.thread:
            self.thread.join()

    def _read_output(self):
        """Read output from the tag subprocess and parse distance data to both beacons"""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                timestamp = time.time()

                # Try to parse JSON format from DWM3001CDK firmware
                # Expected format: {"Block":941, "results":[{"Addr":"0x0001","Status":"Ok","D_cm":39,...},{"Addr":"0x0002","Status":"Ok","D_cm":34,...}]}
                if line.startswith('RAW: '):
                    line = line[5:]  # Remove 'RAW: ' prefix if present

                try:
                    data = json.loads(line)
                    if 'results' in data:
                        for result in data['results']:
                            # Check if this is a valid measurement
                            if result.get('Status') == 'Ok' and 'D_cm' in result and 'Addr' in result:
                                addr = result['Addr']
                                distance_cm = result['D_cm']
                                distance_m = distance_cm / 100.0  # Convert cm to meters

                                # Map address to beacon number
                                # 0x0001 = beacon 1, 0x0002 = beacon 2
                                if addr == '0x0001':
                                    self._add_distance_measurement(
                                        timestamp, 1, distance_m)
                                    logging.debug(
                                        f"[TAG] Distance to Beacon 1: {distance_m:.3f}m")
                                elif addr == '0x0002':
                                    self._add_distance_measurement(
                                        timestamp, 2, distance_m)
                                    logging.debug(
                                        f"[TAG] Distance to Beacon 2: {distance_m:.3f}m")
                        continue
                except json.JSONDecodeError:
                    pass  # Not JSON, skip this line

            except Exception as e:
                if self.running:
                    logging.error(f"Error reading from tag: {e}")

    def _add_distance_measurement(self, timestamp: float, beacon_num: int, distance: float):
        """Add a distance measurement to the appropriate beacon list"""
        if beacon_num == 1:
            self.beacon1_distances.append((timestamp, distance))
            self._cleanup_old_measurements(self.beacon1_distances, timestamp)
        elif beacon_num == 2:
            self.beacon2_distances.append((timestamp, distance))
            self._cleanup_old_measurements(self.beacon2_distances, timestamp)

    def _cleanup_old_measurements(self, distance_list: list, current_time: float):
        """Remove measurements older than the averaging window"""
        cutoff_time = current_time - self.averaging_window
        while distance_list and distance_list[0][0] < cutoff_time:
            distance_list.pop(0)

    def get_averaged_distance(self, beacon_num: int) -> Optional[float]:
        """Get the averaged distance to a specific beacon over the averaging window"""
        current_time = time.time()

        if beacon_num == 1:
            distance_list = self.beacon1_distances
        elif beacon_num == 2:
            distance_list = self.beacon2_distances
        else:
            return None

        # Clean up old measurements
        self._cleanup_old_measurements(distance_list, current_time)

        # Check if we have recent measurements
        if not distance_list:
            return None

        # Check if the most recent measurement is within timeout
        latest_time = distance_list[-1][0]
        if (current_time - latest_time) > DISTANCE_TIMEOUT_SECONDS:
            return None

        # Calculate average distance
        total_distance = sum(dist for _, dist in distance_list)
        count = len(distance_list)

        return total_distance / count if count > 0 else None

    def get_measurement_count(self, beacon_num: int) -> int:
        """Get the number of measurements in the current averaging window"""
        if beacon_num == 1:
            return len(self.beacon1_distances)
        elif beacon_num == 2:
            return len(self.beacon2_distances)
        else:
            return 0


class PositionCalculator:
    """Calculates tag position from beacon distances"""

    def __init__(self, beacon1_pos: Tuple[float, float], beacon2_pos: Tuple[float, float]):
        self.beacon1_pos = beacon1_pos
        self.beacon2_pos = beacon2_pos

    def calculate_position(self, dist1: float, dist2: float) -> Optional[Tuple[float, float]]:
        """
        Calculate tag position using trilateration with two beacons.
        Assumes tag is on the positive Y side of the beacon line.

        Args:
            dist1: Distance to beacon 1
            dist2: Distance to beacon 2

        Returns:
            (x, y) position or None if calculation fails
        """
        # Check if distances are valid
        if dist1 <= 0 or dist2 <= 0:
            return None

        try:
            # Beacon positions
            x1, y1 = self.beacon1_pos
            x2, y2 = self.beacon2_pos

            # Distance between beacons
            if y1 == y2:
                d = abs(x2 - x1)
            else:
                d = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            # Trilateration calculation
            # Using beacon1 as origin for calculation, then transform back
            A = (d**2 - dist2**2 + dist1**2) / (2 * d)

            # Check if solution exists
            discriminant = dist1**2 - A**2
            if discriminant < 0:
                return None

            H = math.sqrt(discriminant)

            # Calculate position relative to beacon line
            if y1 == y2:
                # Beacons are on a horizontal line
                x = A * (x2 - x1) / d + x1
                y = H  # Height above the beacon line
            else:
                # Beacons are at different y positions
                x = A * (x2 - x1) / d + x1
                y = H * (x2 - x1) / d + y1

            # Ensure y is positive (tag above beacon line)
            if y < 0:
                y = abs(y)

            return (x, y)

        except Exception as e:
            logging.debug(f"Position calculation error: {e}")
            return None


class PositioningSystem:
    """Main positioning system coordinator"""

    def __init__(self, tag_port: str, beacon1_port: str, beacon2_port: str):
        self.tag_collector = DistanceCollector(tag_port)
        self.beacon1_port = beacon1_port
        self.beacon2_port = beacon2_port
        self.beacon1_process = None
        self.beacon2_process = None
        self.calculator = PositionCalculator(
            BEACON1_POSITION, BEACON2_POSITION)
        self.running = False

    def start(self):
        """Start all collectors and beacon processes"""
        logging.info("Starting positioning system...")
        logging.debug(
            f"Beacon 1 at {BEACON1_POSITION} on port {self.beacon1_port}")
        logging.debug(
            f"Beacon 2 at {BEACON2_POSITION} on port {self.beacon2_port}")
        logging.debug(f"Tag on port {self.tag_collector.port}")
        logging.debug(
            f"Distance averaging window: {AVERAGING_WINDOW_SECONDS}s")
        logging.debug(f"Position report interval: {REPORT_INTERVAL_SECONDS}s")
        logging.debug("-" * 50)

        # Start beacon processes (they don't output distances, just respond to ranging)
        logging.debug("Starting beacon 1...")
        self.beacon1_process = subprocess.Popen(
            ['python', 'serial_collector.py', '--port',
                self.beacon1_port, 'beacon', '1'],
            stdout=subprocess.DEVNULL,  # Beacons don't output useful data for positioning
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)

        logging.debug("Starting beacon 2...")
        self.beacon2_process = subprocess.Popen(
            ['python', 'serial_collector.py', '--port',
                self.beacon2_port, 'beacon', '2'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)

        # Start tag collector (this will output distances to both beacons)
        logging.debug("Starting tag collector...")
        self.tag_collector.start()
        time.sleep(2)  # Give time for initial ranging to start

        self.running = True
        self._position_reporter()

    def stop(self):
        """Stop all collectors and processes"""
        logging.info("Stopping positioning system...")
        self.running = False

        # Stop tag collector
        self.tag_collector.stop()

        # Stop beacon processes
        if self.beacon1_process:
            self.beacon1_process.terminate()
            self.beacon1_process.wait()

        if self.beacon2_process:
            self.beacon2_process.terminate()
            self.beacon2_process.wait()

    def _position_reporter(self):
        """Main loop that reports position at regular intervals"""
        last_report_time = 0

        try:
            while self.running:
                current_time = time.time()

                # Report position at regular intervals
                if current_time - last_report_time >= REPORT_INTERVAL_SECONDS:
                    self._report_position()
                    last_report_time = current_time

                time.sleep(0.1)  # Small sleep to prevent busy waiting

        except KeyboardInterrupt:
            logging.info("Positioning stopped by user")

    def _report_position(self):
        """Calculate and report current position"""
        # Get averaged distances from tag to both beacons
        dist1 = self.tag_collector.get_averaged_distance(
            1)  # Distance to beacon 1
        dist2 = self.tag_collector.get_averaged_distance(
            2)  # Distance to beacon 2

        timestamp = time.strftime('%H:%M:%S')

        if dist1 is not None and dist2 is not None:
            # Calculate position using trilateration
            position = self.calculator.calculate_position(dist1, dist2)
            if position:
                x, y = position
                count1 = self.tag_collector.get_measurement_count(1)
                count2 = self.tag_collector.get_measurement_count(2)
                logging.info(f"[{timestamp}] Position: x={x:.3f}m, y={y:.3f}m "
                             f"(d1={dist1:.3f}m[n={count1}], d2={dist2:.3f}m[n={count2}])")
            else:
                logging.debug(f"[{timestamp}] Position calculation failed "
                              f"(d1={dist1:.3f}m, d2={dist2:.3f}m)")
        else:
            status = []
            if dist1 is None:
                status.append("no beacon1 data")
            else:
                status.append(f"d1={dist1:.3f}m")

            if dist2 is None:
                status.append("no beacon2 data")
            else:
                status.append(f"d2={dist2:.3f}m")

            logging.debug(
                f"[{timestamp}] Waiting for measurements: {', '.join(status)}")


def main():
    parser = argparse.ArgumentParser(
        description='DWM3001CDK Multi-Device Positioning System')
    parser.add_argument('--tag', required=True,
                        help='Serial port for tag device')
    parser.add_argument('--beacon1', required=True,
                        help='Serial port for beacon 1 device')
    parser.add_argument('--beacon2', required=True,
                        help='Serial port for beacon 2 device')
    parser.add_argument('--list-devices', '-l', action='store_true',
                        help='List available devices and exit')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO',
                                 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: INFO)')

    args = parser.parse_args()

    # Configure logging
    log_format = '%(message)s'  # Simple format for clean output
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=log_format
    )

    if args.list_devices:
        print("Available DWM3001CDK devices:")
        try:
            result = subprocess.run(['python', 'serial_collector.py', '--list-devices'],
                                    capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"Error listing devices: {e}")
        return

    # Create and start positioning system
    system = PositioningSystem(args.tag, args.beacon1, args.beacon2)

    try:
        system.start()
    except KeyboardInterrupt:
        pass
    finally:
        system.stop()


if __name__ == "__main__":
    main()
