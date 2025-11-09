# DWM3001CDK Python Wrapper

Python interface for DWM3001CDK UWB ranging devices with real-time positioning capabilities.

## Features

- ✅ Serial communication with DWM3001CDK devices
- ✅ JSON parsing of ranging data from firmware
- ✅ Multiple output formats (JSON, CSV, compact, raw)
- ✅ Multi-device positioning system (2 beacons + 1 tag)
- ✅ Real-time trilateration for 2D position calculation
- ✅ Distance averaging and filtering
- ✅ Configurable logging levels

## Setup

### Option 1: Automated Setup
```bash
./setup.sh
source venv/bin/activate
```

### Option 2: Manual Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Find Devices
```bash
python serial_collector.py --list-devices
```

### Basic Operations

#### Start as Tag (Initiator)
The tag measures distances to all beacons:
```bash
# Default format (compact, human-readable)
python serial_collector.py --port /dev/ttyACM0 tag

# JSON format (structured data)
python serial_collector.py --port /dev/ttyACM0 --format json tag

# CSV format (easy parsing)
python serial_collector.py --port /dev/ttyACM0 --format csv tag

# Raw format (firmware output)
python serial_collector.py --port /dev/ttyACM0 --format raw tag
```

#### Start as Beacon (Responder)
Beacons respond to tag ranging requests:
```bash
# Start as beacon 1
python serial_collector.py --port /dev/ttyACM1 beacon 1

# Start as beacon 2
python serial_collector.py --port /dev/ttyACM2 beacon 2
```

### Multi-Device Positioning System

The `example_usage.py` script orchestrates a complete positioning system with 2 beacons and 1 tag.

#### Basic Usage
```bash
# Run with default INFO logging (clean output, positioning results only)
python example_usage.py \
    --beacon1 /dev/ttyACM0 \
    --beacon2 /dev/ttyACM1 \
    --tag /dev/ttyACM2
```

**Output (INFO level):**
```
Starting positioning system...
[18:11:01] Position: x=0.621m, y=0.000m (d1=1.403m[n=82], d2=1.313m[n=82])
[18:11:02] Position: x=0.509m, y=0.000m (d1=1.392m[n=83], d2=1.386m[n=83])
[18:11:03] Position: x=0.417m, y=0.000m (d1=1.391m[n=54], d2=1.449m[n=54])
```

#### Debug Mode
```bash
# Run with DEBUG logging (verbose output, all distance measurements)
python example_usage.py \
    --beacon1 /dev/ttyACM0 \
    --beacon2 /dev/ttyACM1 \
    --tag /dev/ttyACM2 \
    --log-level DEBUG
```

**Output (DEBUG level):**
```
Starting positioning system...
Beacon 1 at (0.0, 0.0) on port /dev/ttyACM0
Beacon 2 at (1.0, 0.0) on port /dev/ttyACM1
Tag on port /dev/ttyACM2
Distance averaging window: 2.0s
Position report interval: 1.0s
--------------------------------------------------
Starting beacon 1...
Starting beacon 2...
Starting tag collector...
[TAG] Distance to Beacon 1: 1.590m
[TAG] Distance to Beacon 2: 0.750m
[TAG] Distance to Beacon 1: 1.440m
[TAG] Distance to Beacon 2: 0.580m
[18:11:01] Position: x=0.621m, y=0.000m (d1=1.403m[n=82], d2=1.313m[n=82])
```

#### Logging Levels

- `INFO` (default): Position results only - clean output for production
- `DEBUG`: All details including individual distance measurements
- `WARNING`: Warnings and errors only
- `ERROR`: Errors only
- `CRITICAL`: Critical errors only

```bash
# Specify custom log level
python example_usage.py \
    --beacon1 /dev/ttyACM0 \
    --beacon2 /dev/ttyACM1 \
    --tag /dev/ttyACM2 \
    --log-level WARNING
```

## System Architecture

### Positioning System Configuration

The system uses **2 beacons at fixed positions** and **1 mobile tag**:

- **Beacon 1**: Position (0.0, 0.0) - Origin point
- **Beacon 2**: Position (1.0, 0.0) - 1 meter on X-axis
- **Tag**: Mobile device, position calculated via trilateration

### How It Works

1. **Tag** initiates ranging with both beacons
2. **Beacons** respond with ranging information
3. **Tag** measures distances to both beacons (outputs JSON format)
4. **Python script** parses distances and calculates 2D position using trilateration
5. **Position** is reported at 1-second intervals with averaged distances (2-second window)

### Data Flow

```
DWM3001CDK Firmware → JSON Output → serial_collector.py → example_usage.py → Position
{"Block":941, "results":[{"Addr":"0x0001", "D_cm":39, ...}]}
```

## Output Formats

### JSON Format
```json
{
  "timestamp": "2025-11-09T17:59:14.974047",
  "block": 3194,
  "results": [
    {
      "timestamp": "2025-11-09T17:59:14.974031",
      "block": 3194,
      "address": "0x0001",
      "distance_cm": 44,
      "distance_m": 0.44,
      "pdoa_deg": 0.0,
      "laoa_deg": 0.0,
      "raoa_deg": 0.0,
      "fom": 0,
      "cfo_100ppm": 615
    }
  ],
  "count": 1
}
```

### CSV Format
```
2025-11-09T18:00:27.777330,4136,0x0001,0.48,48,0.0,0.0,0.0,0,567
```

### Compact Format
```
Block 4501 | 0x0001:0.420m, 0x0002:0.290m
```

## Troubleshooting

### Position Calculation Issues

If you see "Position calculation failed" messages, this typically means:

1. **Invalid geometry**: The measured distances don't form a valid triangle
2. **Beacons too close**: Try increasing the distance between beacons
3. **Measurement errors**: UWB signals may have multipath interference
4. **Collinear configuration**: Ensure tag, beacon1, and beacon2 don't form a straight line

**Solutions:**
- Space beacons at least 1-2 meters apart
- Position tag to form a triangle with beacons (not in a line)
- Ensure clear line-of-sight between devices
- Check for metal objects or obstacles causing reflections

### Serial Port Permissions

If you get permission errors:
```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### No Data from Devices

1. Check device connections: `python serial_collector.py --list-devices`
2. Verify correct ports are specified
3. Try running in DEBUG mode to see raw communication
4. Ensure firmware is properly flashed on devices

## Configuration

You can modify these parameters in `example_usage.py`:

```python
BEACON1_POSITION = (0.0, 0.0)     # Beacon 1 at origin
BEACON2_POSITION = (1.0, 0.0)     # Beacon 2 at (1m, 0m)
REPORT_INTERVAL = 1.0             # Report position every 1 second
DISTANCE_TIMEOUT = 5.0            # Timeout for distance measurements
AVERAGING_WINDOW = 2.0            # Average distances over 2 seconds
```

## Files

- `serial_collector.py` - Core serial interface for DWM3001CDK
  - Device discovery and connection
  - JSON parsing of firmware output
  - Multiple output format support
  - Tag and beacon mode management

- `example_usage.py` - Multi-device positioning system
  - Coordinates 2 beacons + 1 tag
  - Real-time distance collection
  - 2D trilateration algorithm
  - Distance averaging and filtering
  - Configurable logging levels

- `setup.sh` - Environment setup script
- `requirements.txt` - Python dependencies (pyserial)

## Dependencies

- Python 3.7+
- pyserial - Serial port communication

Install via:
```bash
pip install -r requirements.txt
```