#!/usr/bin/env python3
"""
Dummy IoT Device Simulator for DWM3001CDK Positioning System

Simulates a positioning device that plays back keyframe animations
and sends position data to Azure IoT Hub or stdout.
"""

import argparse
import time
import logging
import random
from typing import Dict, List, Tuple, Optional
from azure_iot_reporter import AzureIoTReporter, is_azure_iot_available


class KeyframeAnimator:
    """Plays back position keyframes with interpolation"""

    def __init__(self, keyframes: Dict[float, Tuple[float, float]], 
                 back_and_forth: bool = False,
                 pause_seconds: float = 0.0,
                 noise_cm: Tuple[float, float] = (0.0, 0.0)):
        """
        Initialize keyframe animator
        
        Args:
            keyframes: Dict mapping timestamp (seconds) to (x, y) position in meters
            back_and_forth: If True, play forward then backward
            pause_seconds: Pause duration between animation cycles
            noise_cm: Random noise to add to x,y in centimeters (x_noise, y_noise)
        """
        # Sort keyframes by timestamp
        self.keyframes = sorted(keyframes.items())
        if not self.keyframes:
            raise ValueError("At least one keyframe is required")
        
        self.back_and_forth = back_and_forth
        self.pause_seconds = pause_seconds
        self.noise_cm = noise_cm
        
        # Calculate total animation duration
        self.duration = self.keyframes[-1][0] - self.keyframes[0][0]
        
        # Animation state
        self.start_time = None
        self.forward = True
        self.paused = False
        self.pause_start = None
        
    def start(self):
        """Start the animation"""
        self.start_time = time.time()
        self.forward = True
        self.paused = False
        
    def get_position(self) -> Tuple[float, float]:
        """
        Get current interpolated position with noise
        
        Returns:
            (x, y) position in meters
        """
        if self.start_time is None:
            return self.keyframes[0][1]
        
        elapsed = time.time() - self.start_time
        
        # Handle pausing between cycles
        if self.paused:
            if self.pause_start is None:
                self.pause_start = time.time()
            
            if time.time() - self.pause_start >= self.pause_seconds:
                # Resume animation
                self.paused = False
                self.pause_start = None
                self.start_time = time.time()
                elapsed = 0
            else:
                # Still paused, return last position
                if self.forward:
                    pos = self.keyframes[-1][1]
                else:
                    pos = self.keyframes[0][1]
                return self._add_noise(pos)
        
        # Calculate position in animation cycle
        if self.back_and_forth:
            cycle_duration = self.duration * 2  # Forward + backward
            elapsed_in_cycle = elapsed % (cycle_duration + self.pause_seconds)
            
            if elapsed_in_cycle < self.duration:
                # Forward motion
                self.forward = True
                local_time = elapsed_in_cycle
            elif elapsed_in_cycle < self.duration * 2:
                # Backward motion
                self.forward = False
                local_time = self.duration * 2 - elapsed_in_cycle
            else:
                # Pause period
                self.paused = True
                self.pause_start = time.time()
                pos = self.keyframes[-1][1] if self.forward else self.keyframes[0][1]
                return self._add_noise(pos)
        else:
            # Forward only with pause
            cycle_duration = self.duration + self.pause_seconds
            elapsed_in_cycle = elapsed % cycle_duration
            
            if elapsed_in_cycle >= self.duration:
                # Pause period
                self.paused = True
                self.pause_start = time.time()
                return self._add_noise(self.keyframes[-1][1])
            
            local_time = elapsed_in_cycle
        
        # Interpolate position between keyframes
        pos = self._interpolate_position(local_time)
        return self._add_noise(pos)
    
    def _interpolate_position(self, t: float) -> Tuple[float, float]:
        """
        Interpolate position at time t
        
        Args:
            t: Time in seconds from start of animation
        
        Returns:
            (x, y) position in meters
        """
        # Add offset to match keyframe timestamps
        t = t + self.keyframes[0][0]
        
        # Find surrounding keyframes
        if t <= self.keyframes[0][0]:
            return self.keyframes[0][1]
        
        if t >= self.keyframes[-1][0]:
            return self.keyframes[-1][1]
        
        # Find the two keyframes to interpolate between
        for i in range(len(self.keyframes) - 1):
            t1, (x1, y1) = self.keyframes[i]
            t2, (x2, y2) = self.keyframes[i + 1]
            
            if t1 <= t <= t2:
                # Linear interpolation
                if t2 == t1:
                    return (x1, y1)
                
                ratio = (t - t1) / (t2 - t1)
                x = x1 + (x2 - x1) * ratio
                y = y1 + (y2 - y1) * ratio
                return (x, y)
        
        return self.keyframes[-1][1]
    
    def _add_noise(self, pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        Add random noise to position
        
        Args:
            pos: (x, y) position in meters
        
        Returns:
            Position with noise added
        """
        x, y = pos
        noise_x_cm, noise_y_cm = self.noise_cm
        
        if noise_x_cm != 0.0:
            x += random.uniform(-noise_x_cm, noise_x_cm) / 100.0  # Convert cm to m
        
        if noise_y_cm != 0.0:
            y += random.uniform(-noise_y_cm, noise_y_cm) / 100.0  # Convert cm to m
        
        return (x, y)


class DummyIoTDevice:
    """Simulates an IoT device sending position data"""
    
    def __init__(self, 
                 keyframes: Dict[float, Tuple[float, float]],
                 beacon1_position: Tuple[float, float] = (0.0, 0.0),
                 beacon2_position: Tuple[float, float] = (2.0, 0.0),
                 back_and_forth: bool = False,
                 pause_seconds: float = 0.0,
                 noise_cm: Tuple[float, float] = (0.0, 0.0),
                 dry_run: bool = False,
                 report_interval: float = 1.0,
                 azure_connection_string: Optional[str] = None,
                 azure_device_id: str = "dwm3001cdk-dummy"):
        """
        Initialize dummy IoT device
        
        Args:
            keyframes: Dict mapping timestamp to (x, y) position
            beacon1_position: Fixed beacon 1 position (x, y) in meters
            beacon2_position: Fixed beacon 2 position (x, y) in meters
            back_and_forth: Play animation forward then backward
            pause_seconds: Pause between animation cycles
            noise_cm: Random noise (x_noise, y_noise) in centimeters
            dry_run: If True, print to stdout instead of sending to IoT Hub
            report_interval: Seconds between position reports
            azure_connection_string: Azure IoT Hub connection string
            azure_device_id: Device ID for Azure IoT Hub
        """
        self.animator = KeyframeAnimator(keyframes, back_and_forth, pause_seconds, noise_cm)
        self.beacon1_position = beacon1_position
        self.beacon2_position = beacon2_position
        self.dry_run = dry_run
        self.report_interval = report_interval
        self.running = False
        
        # Azure IoT Hub setup
        self.azure_reporter = None
        if not dry_run and azure_connection_string:
            try:
                if not is_azure_iot_available():
                    logging.error("Azure IoT SDK not installed. Install with: pip install azure-iot-device")
                    logging.info("Falling back to dry-run mode")
                    self.dry_run = True
                else:
                    self.azure_reporter = AzureIoTReporter(azure_connection_string, azure_device_id)
                    logging.info("Azure IoT Hub reporter initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Azure IoT reporter: {e}")
                logging.info("Falling back to dry-run mode")
                self.dry_run = True
    
    def start(self):
        """Start sending position data"""
        logging.info("Starting dummy IoT device...")
        
        if self.dry_run:
            logging.info("DRY RUN MODE - Outputting to stdout only")
        else:
            if self.azure_reporter:
                try:
                    self.azure_reporter.connect()
                    self.azure_reporter.send_status("online", {
                        "type": "dummy_device",
                        "beacon1_position": self.beacon1_position,
                        "beacon2_position": self.beacon2_position,
                        "animation_mode": "back_and_forth" if self.animator.back_and_forth else "forward_only"
                    })
                    logging.info("Connected to Azure IoT Hub")
                except Exception as e:
                    logging.error(f"Failed to connect to Azure IoT Hub: {e}")
                    logging.info("Falling back to dry-run mode")
                    self.dry_run = True
        
        self.animator.start()
        self.running = True
        
        try:
            self._run_loop()
        except KeyboardInterrupt:
            logging.info("\nStopped by user")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the device"""
        logging.info("Stopping dummy IoT device...")
        self.running = False
        
        if self.azure_reporter:
            try:
                self.azure_reporter.send_status("offline")
                self.azure_reporter.disconnect()
            except Exception as e:
                logging.error(f"Error disconnecting from Azure IoT Hub: {e}")
    
    def _run_loop(self):
        """Main loop that reports position at regular intervals"""
        while self.running:
            # Get current position
            x, y = self.animator.get_position()
            
            # Calculate distances to beacons (simulated)
            dist1 = self._calculate_distance((x, y), self.beacon1_position)
            dist2 = self._calculate_distance((x, y), self.beacon2_position)
            
            # Report position
            timestamp = time.strftime('%H:%M:%S')
            
            if self.dry_run:
                # Print to stdout
                print(f"[{timestamp}] Position: x={x:.3f}m, y={y:.3f}m "
                      f"(d1={dist1:.3f}m, d2={dist2:.3f}m)")
            else:
                # Send to Azure IoT Hub
                logging.info(f"[{timestamp}] Position: x={x:.3f}m, y={y:.3f}m "
                            f"(d1={dist1:.3f}m, d2={dist2:.3f}m)")
                
                if self.azure_reporter:
                    try:
                        self.azure_reporter.send_position_data(
                            x, y, dist1, dist2,
                            measurement_count1=10,  # Simulated measurement count
                            measurement_count2=10
                        )
                    except Exception as e:
                        logging.debug(f"Failed to send to Azure IoT Hub: {e}")
            
            # Wait for next report interval
            time.sleep(self.report_interval)
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions"""
        x1, y1 = pos1
        x2, y2 = pos2
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def parse_keyframes(keyframe_str: str) -> Dict[float, Tuple[float, float]]:
    """
    Parse keyframes from string format
    
    Format: "t1:x1,y1;t2:x2,y2;..."
    Example: "0:0.5,0.5;5:1.5,1.0;10:0.5,1.5"
    
    Args:
        keyframe_str: Keyframe string
    
    Returns:
        Dict mapping timestamp to (x, y) position
    """
    keyframes = {}
    
    for frame in keyframe_str.split(';'):
        frame = frame.strip()
        if not frame:
            continue
        
        try:
            time_part, pos_part = frame.split(':')
            t = float(time_part)
            x, y = map(float, pos_part.split(','))
            keyframes[t] = (x, y)
        except ValueError as e:
            raise ValueError(f"Invalid keyframe format: {frame}. Expected 't:x,y'. Error: {e}")
    
    return keyframes


def main():
    parser = argparse.ArgumentParser(
        description='Dummy IoT Device Simulator for DWM3001CDK Positioning',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple forward animation with 2 second pause
  python dummy_iot_device.py --keyframes "0:0.5,0.5;5:1.5,1.0;10:0.5,1.5" --pause 2 --dry-run
  
  # Back-and-forth animation with noise
  python dummy_iot_device.py --keyframes "0:0.5,0.5;5:1.5,1.0;10:0.5,1.5" --back-and-forth --noise 5,3 --dry-run
  
  # Send to Azure IoT Hub
  python dummy_iot_device.py --keyframes "0:0.5,0.5;5:1.5,1.0" --azure-connection-string "$AZURE_CONNECTION_STRING"
        """)
    
    parser.add_argument('--keyframes', required=True,
                        help='Keyframes in format "t1:x1,y1;t2:x2,y2;..." (time in seconds, position in meters)')
    parser.add_argument('--back-and-forth', action='store_true',
                        help='Play animation forward then backward')
    parser.add_argument('--pause', type=float, default=0.0,
                        help='Pause duration in seconds between animation cycles (default: 0)')
    parser.add_argument('--noise', type=str, default='0,0',
                        help='Random noise for x,y in centimeters, format "x,y" (default: 0,0)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print position data to stdout instead of sending to IoT Hub')
    parser.add_argument('--report-interval', type=float, default=1.0,
                        help='Seconds between position reports (default: 1.0)')
    parser.add_argument('--beacon1-pos', type=str, default='0.0,0.0',
                        help='Beacon 1 position "x,y" in meters (default: 0.0,0.0)')
    parser.add_argument('--beacon2-pos', type=str, default='2.0,0.0',
                        help='Beacon 2 position "x,y" in meters (default: 2.0,0.0)')
    parser.add_argument('--azure-connection-string',
                        help='Azure IoT Hub device connection string')
    parser.add_argument('--azure-device-id', default='dwm3001cdk-dummy',
                        help='Azure IoT Hub device ID (default: dwm3001cdk-dummy)')
    parser.add_argument('--log-level', default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Configure logging
    log_format = '%(message)s'
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=log_format
    )
    
    # Parse keyframes
    try:
        keyframes = parse_keyframes(args.keyframes)
        if not keyframes:
            parser.error("At least one keyframe is required")
        logging.debug(f"Parsed keyframes: {keyframes}")
    except ValueError as e:
        parser.error(str(e))
    
    # Parse noise
    try:
        noise_x, noise_y = map(float, args.noise.split(','))
        noise_cm = (noise_x, noise_y)
    except ValueError:
        parser.error(f"Invalid noise format: {args.noise}. Expected 'x,y'")
    
    # Parse beacon positions
    try:
        beacon1_x, beacon1_y = map(float, args.beacon1_pos.split(','))
        beacon1_position = (beacon1_x, beacon1_y)
    except ValueError:
        parser.error(f"Invalid beacon1 position: {args.beacon1_pos}. Expected 'x,y'")
    
    try:
        beacon2_x, beacon2_y = map(float, args.beacon2_pos.split(','))
        beacon2_position = (beacon2_x, beacon2_y)
    except ValueError:
        parser.error(f"Invalid beacon2 position: {args.beacon2_pos}. Expected 'x,y'")
    
    # Create and start device
    device = DummyIoTDevice(
        keyframes=keyframes,
        beacon1_position=beacon1_position,
        beacon2_position=beacon2_position,
        back_and_forth=args.back_and_forth,
        pause_seconds=args.pause,
        noise_cm=noise_cm,
        dry_run=args.dry_run,
        report_interval=args.report_interval,
        azure_connection_string=args.azure_connection_string,
        azure_device_id=args.azure_device_id
    )
    
    device.start()


if __name__ == "__main__":
    main()
