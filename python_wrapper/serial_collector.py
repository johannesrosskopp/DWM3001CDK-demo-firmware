#!/usr/bin/env python3
"""
DWM3001CDK Serial Data Collector

Collects data from DWM3001CDK via serial port, performs minimal processing,
and outputs to stdout (can be extended for Azure IoT later).
"""

import serial
import serial.tools.list_ports
import json
import time
import argparse
import sys
import re
from datetime import datetime
from typing import Optional, Dict, Any


class DWM3001Collector:
    def __init__(self, baudrate: int = 115200, timeout: float = 1.0):
        self.port = None
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        
        # FiRa session parameters (can be customized)
        self.rframe_bprf = 4
        self.slot_duration = 2400
        self.block_duration = 200
        self.round_duration = 25
        self.rr_usage = 2
        self.session_id = 42
        self.vupper64 = "01:02:03:04:05:06:07:08"
        self.multi_node_mode = 1
        self.round_hopping = 0
        self.initiator_addr = 0
        
    def find_dwm3001_devices(self) -> list:
        """Find all connected DWM3001CDK devices"""
        devices = []
        for port in serial.tools.list_ports.comports():
            # Look for the specific USB VID:PID for DWM3001CDK (Qorvo/SEGGER J-Link)
            if port.vid == 0x1915 and port.pid == 0x520f:
                devices.append({
                    'device': port.device,
                    'description': port.description,
                    'serial_number': port.serial_number,
                    'hwid': port.hwid
                })
        return devices
    
    def connect(self, port: str) -> bool:
        """Connect to the serial device"""
        self.port = port
        
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            print(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the serial device"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Disconnected from serial device")
    
    def send_command(self, command: str) -> bool:
        """Send a command to the device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False
        
        try:
            cmd_bytes = (command + '\r\n').encode('utf-8')
            self.serial_conn.write(cmd_bytes)
            print(f"Sent command: {command}")
            return True
        except Exception as e:
            print(f"Error sending command '{command}': {e}")
            return False
    
    def read_line(self) -> Optional[str]:
        """Read a line from the serial device"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return None
        
        try:
            line = self.serial_conn.readline().decode('utf-8').strip()
            return line if line else None
        except Exception as e:
            print(f"Error reading from serial: {e}")
            return None
    
    def start_tag(self, duration: Optional[float] = None, output_format: str = 'compact') -> None:
        """Start the device as a tag (initiator) in FiRa ranging"""
        if not self.serial_conn or not self.serial_conn.is_open:
            print("Error: Not connected to device")
            return
        
        # Build the INITF command with current parameters
        initf_cmd = (f"initf {self.rframe_bprf} {self.slot_duration} {self.block_duration} "
                    f"{self.round_duration} {self.rr_usage} {self.session_id} {self.vupper64} "
                    f"{self.multi_node_mode} {self.round_hopping} {self.initiator_addr} 1 2")
        
        print(f"Starting tag mode with command: {initf_cmd}")
        success = self.send_command(initf_cmd)
        
        if not success:
            print("Failed to send INITF command")
            return
        
        # Start data collection
        print("Tag started. Collecting ranging data...")
        if duration:
            print(f"Will run for {duration} seconds")
        else:
            print("Running indefinitely (Ctrl+C to stop)")
        
        try:
            start_time = time.time()
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break
                
                line = self.read_line()
                if line:
                    parsed_data = self.parse_ranging_data(line)
                    if parsed_data:
                        self.output_data(parsed_data, output_format)
                    else:
                        # Show raw output only if parsing failed and format is raw
                        if output_format == 'raw':
                            print(f"RAW: {line}")
                        
        except KeyboardInterrupt:
            print("\nTag operation stopped by user")
        except Exception as e:
            print(f"Error during tag operation: {e}")
    
    def start_beacon(self, beacon_number: int, duration: Optional[float] = None, output_format: str = 'compact') -> None:
        """Start the device as a beacon (responder) in FiRa ranging
        
        Args:
            beacon_number: 1 or 2 to specify which responder address to use
            duration: How long to run in seconds, None for infinite
            output_format: Format for output ('json', 'csv', 'compact', 'raw')
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("Error: Not connected to device")
            return
        
        if beacon_number not in [1, 2]:
            print("Error: beacon_number must be 1 or 2")
            return
        
        # Build the RESPF command with current parameters
        respf_cmd = (f"respf {self.rframe_bprf} {self.slot_duration} {self.block_duration} "
                    f"{self.round_duration} {self.rr_usage} {self.session_id} {self.vupper64} "
                    f"{self.multi_node_mode} {self.round_hopping} {self.initiator_addr} {beacon_number}")
        
        print(f"Starting beacon {beacon_number} mode with command: {respf_cmd}")
        success = self.send_command(respf_cmd)
        
        if not success:
            print("Failed to send RESPF command")
            return
        
        # Start data collection
        print(f"Beacon {beacon_number} started. Monitoring for ranging...")
        if duration:
            print(f"Will run for {duration} seconds")
        else:
            print("Running indefinitely (Ctrl+C to stop)")
        
        try:
            start_time = time.time()
            while True:
                if duration and (time.time() - start_time) >= duration:
                    break
                
                line = self.read_line()
                if line:
                    parsed_data = self.parse_ranging_data(line)
                    if parsed_data:
                        self.output_data(parsed_data, output_format)
                    else:
                        # Show raw output only if parsing failed and format is raw
                        if output_format == 'raw':
                            print(f"RAW: {line}")
                        
        except KeyboardInterrupt:
            print(f"\nBeacon {beacon_number} operation stopped by user")
        except Exception as e:
            print(f"Error during beacon operation: {e}")
    
    def parse_ranging_data(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse ranging data from DWM3001CDK output
        
        The DWM3001CDK firmware outputs JSON format:
        {"Block":941, "results":[{"Addr":"0x0001","Status":"Ok","D_cm":39,"LPDoA_deg":0.00,...},...]}
        """
        # Try to parse as JSON first (DWM3001CDK format)
        try:
            data = json.loads(line)
            if 'results' in data and 'Block' in data:
                # This is DWM3001CDK JSON format
                parsed_results = []
                block_num = data['Block']
                
                for result in data['results']:
                    if result.get('Status') == 'Ok':
                        parsed_result = {
                            'timestamp': datetime.now().isoformat(),
                            'block': block_num,
                            'address': result.get('Addr', 'Unknown'),
                            'distance_cm': result.get('D_cm'),
                            'distance_m': result.get('D_cm', 0) / 100.0,
                            'pdoa_deg': result.get('LPDoA_deg', 0.0),
                            'laoa_deg': result.get('LAoA_deg', 0.0),
                            'raoa_deg': result.get('RAoA_deg', 0.0),
                            'fom': result.get('LFoM', 0),
                            'cfo_100ppm': result.get('CFO_100ppm', 0)
                        }
                        parsed_results.append(parsed_result)
                
                # Return the parsed results if any
                if parsed_results:
                    return {
                        'timestamp': datetime.now().isoformat(),
                        'block': block_num,
                        'results': parsed_results,
                        'count': len(parsed_results)
                    }
        except json.JSONDecodeError:
            pass  # Not JSON, try other patterns
        
        # Fallback: Look for other patterns (for non-JSON output)
        distance_pattern = r'dist:\s*(\d+\.?\d*)\s*m'
        rssi_pattern = r'rssi:\s*(-?\d+\.?\d*)\s*dBm'
        timestamp_pattern = r'ts:\s*(\d+)'
        
        parsed_data = {
            'timestamp': datetime.now().isoformat(),
            'raw_line': line
        }
        
        # Extract distance
        distance_match = re.search(distance_pattern, line, re.IGNORECASE)
        if distance_match:
            parsed_data['distance_m'] = float(distance_match.group(1))
        
        # Extract RSSI
        rssi_match = re.search(rssi_pattern, line, re.IGNORECASE)
        if rssi_match:
            parsed_data['rssi_dbm'] = float(rssi_match.group(1))
        
        # Extract timestamp
        ts_match = re.search(timestamp_pattern, line, re.IGNORECASE)
        if ts_match:
            parsed_data['device_timestamp'] = int(ts_match.group(1))
        
        # Only return parsed data if we found some useful information
        if any(key in parsed_data for key in ['distance_m', 'rssi_dbm', 'device_timestamp']):
            return parsed_data
        
        return None
    
    def collect_data(self, duration: Optional[float] = None, output_format: str = 'json'):
        """Collect data from the device (requires connection to be established first)"""
        if not self.serial_conn or not self.serial_conn.is_open:
            print("Error: Not connected to device. Use connect(port) first.")
            return
        
        print(f"Starting data collection (format: {output_format})")
        if duration:
            print(f"Collection will run for {duration} seconds")
        else:
            print("Collection will run indefinitely (Ctrl+C to stop)")
        
        start_time = time.time()
        
        try:
            while True:
                # Check duration limit
                if duration and (time.time() - start_time) >= duration:
                    break
                
                line = self.read_line()
                if not line:
                    continue
                
                # Parse the data
                parsed_data = self.parse_ranging_data(line)
                
                if parsed_data:
                    # Process and output the data
                    self.output_data(parsed_data, output_format)
                else:
                    # Output raw line if no parsing was successful
                    if output_format == 'raw':
                        print(f"RAW: {line}")
        
        except KeyboardInterrupt:
            print("\nData collection stopped by user")
        except Exception as e:
            print(f"Error during data collection: {e}")
    
    def output_data(self, data: Dict[str, Any], format_type: str = 'json'):
        """Output processed data"""
        if format_type == 'json':
            print(json.dumps(data, indent=2))
        elif format_type == 'csv':
            # For DWM3001CDK multi-result format
            if 'results' in data:
                for result in data['results']:
                    values = [
                        result.get('timestamp', ''),
                        result.get('block', ''),
                        result.get('address', ''),
                        result.get('distance_m', ''),
                        result.get('distance_cm', ''),
                        result.get('pdoa_deg', ''),
                        result.get('laoa_deg', ''),
                        result.get('raoa_deg', ''),
                        result.get('fom', ''),
                        result.get('cfo_100ppm', '')
                    ]
                    print(','.join(str(v) for v in values))
            else:
                # Legacy format
                values = [
                    data.get('timestamp', ''),
                    data.get('distance_m', ''),
                    data.get('rssi_dbm', ''),
                    data.get('device_timestamp', '')
                ]
                print(','.join(str(v) for v in values))
        elif format_type == 'compact':
            # For DWM3001CDK multi-result format
            if 'results' in data:
                block = data.get('block', 'N/A')
                results_str = []
                for result in data['results']:
                    addr = result.get('address', 'N/A')
                    dist = result.get('distance_m', 'N/A')
                    if dist != 'N/A':
                        dist = f"{dist:.3f}"
                    results_str.append(f"{addr}:{dist}m")
                print(f"Block {block} | {', '.join(results_str)}")
            else:
                # Legacy format
                ts = data.get('timestamp', '')[:19]  # Trim to seconds
                dist = data.get('distance_m', 'N/A')
                rssi = data.get('rssi_dbm', 'N/A')
                print(f"{ts} | Distance: {dist}m | RSSI: {rssi}dBm")
        elif format_type == 'raw':
            # For raw format, output the original data structure
            if 'results' in data:
                # Convert back to DWM3001CDK-like format for raw output
                raw_output = {
                    'Block': data.get('block'),
                    'results': []
                }
                for result in data['results']:
                    raw_result = {
                        'Addr': result.get('address'),
                        'Status': 'Ok',
                        'D_cm': result.get('distance_cm'),
                        'LPDoA_deg': result.get('pdoa_deg'),
                        'LAoA_deg': result.get('laoa_deg'),
                        'RAoA_deg': result.get('raoa_deg'),
                        'LFoM': result.get('fom'),
                        'CFO_100ppm': result.get('cfo_100ppm')
                    }
                    raw_output['results'].append(raw_result)
                print(json.dumps(raw_output))
            else:
                print(data.get('raw_line', str(data)))
        else:
            print(data)


def main():
    parser = argparse.ArgumentParser(
        description='DWM3001CDK Serial Data Collector',
        epilog='Use --list-devices to find available ports, then specify --port for operations.'
    )
    parser.add_argument('--port', '-p', help='Serial port (required for device operations, get from --list-devices)')
    parser.add_argument('--baudrate', '-b', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--duration', '-d', type=float, help='Operation duration in seconds (infinite if not specified)')
    parser.add_argument('--format', '-f', choices=['json', 'csv', 'compact', 'raw'], default='compact', 
                       help='Output format (default: compact)')
    parser.add_argument('--list-devices', '-l', action='store_true', help='List available DWM3001CDK devices')
    parser.add_argument('--send-command', '-c', help='Send a command to the device (requires --port)')
    parser.add_argument('command', nargs='?', choices=['tag', 'beacon'], 
                       help='Command to execute: tag (initiator) or beacon (responder)')
    parser.add_argument('beacon_number', nargs='?', type=int, choices=[1, 2], 
                       help='Beacon number (1 or 2) when using beacon command')
    
    args = parser.parse_args()
    
    # Check if any action was specified
    device_operations = (args.send_command or args.command)
    
    if not (args.list_devices or device_operations):
        parser.print_help()
        return
    
    collector = DWM3001Collector(baudrate=args.baudrate)
    
    # List devices operation (doesn't require port)
    if args.list_devices:
        devices = collector.find_dwm3001_devices()
        if devices:
            print("Available DWM3001CDK devices:")
            for device in devices:
                print(f"  {device['device']} - {device['description']} (SN: {device['serial_number']})")
            print("\nUse --port <device> to connect to a specific device.")
        else:
            print("No DWM3001CDK devices found")
        return
    
    # All device operations require explicit port
    if device_operations and not args.port:
        print("Error: --port is required for device operations.")
        print("Use --list-devices to find available devices, then specify --port.")
        return
    
    # Validate beacon command arguments
    if args.command == 'beacon' and not args.beacon_number:
        print("Error: beacon command requires beacon number (1 or 2)")
        print("Usage: python serial_collector.py --port <port> beacon <1|2>")
        return
    
    if args.command == 'tag' and args.beacon_number:
        print("Warning: beacon number ignored for tag command")
    
    # Connect to device
    print(f"Connecting to {args.port}...")
    if not collector.connect(args.port):
        print("Failed to connect to device")
        return
    
    try:
        # Send initial command if specified
        if args.send_command:
            collector.send_command(args.send_command)
            time.sleep(1)  # Give device time to process
        
        # Execute command
        if args.command == 'tag':
            collector.start_tag(duration=args.duration, output_format=args.format)
        elif args.command == 'beacon':
            collector.start_beacon(args.beacon_number, duration=args.duration, output_format=args.format)
    
    finally:
        collector.disconnect()


if __name__ == "__main__":
    main()