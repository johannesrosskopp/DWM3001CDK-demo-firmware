# DWM3001CDK Python Wrapper

Python interface for DWM3001CDK UWB ranging devices with real-time positioning capabilities.

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

#### Debug Mode
```bash
# Run with DEBUG logging (verbose output, all distance measurements)
python example_usage.py \
    --beacon1 /dev/ttyACM0 \
    --beacon2 /dev/ttyACM1 \
    --tag /dev/ttyACM2 \
    --log-level DEBUG
```

### Azure IoT Hub Integration

Send positioning data to Azure IoT Hub for cloud-based tracking and analytics.

#### Usage with Azure IoT Hub

```bash
python example_usage.py \
    --beacon1 /dev/ttyACM0 \
    --beacon2 /dev/ttyACM1 \
    --tag /dev/ttyACM2 \
    --azure-connection-string "HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=..." \
    --azure-device-id "dwm3001cdk-tag"
```

#### What Data is Sent

**Position Telemetry:**
```json
{
  "deviceId": "dwm3001cdk-tag",
  "timestamp": "2025-11-09T18:30:45.123456Z",
  "position": {
    "x": 1.234,
    "y": 0.567,
    "unit": "meters"
  },
  "distances": {
    "beacon1": {
      "distance": 1.403,
      "measurementCount": 82
    },
    "beacon2": {
      "distance": 1.313,
      "measurementCount": 82
    }
  },
  "messageId": 42
}
```