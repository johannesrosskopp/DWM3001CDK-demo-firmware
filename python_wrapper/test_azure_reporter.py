#!/usr/bin/env python3
"""
Test script for Azure IoT Reporter
Tests the reporter functionality without requiring actual Azure connection
"""

import sys
import json

# Mock the Azure IoT SDK if not installed
try:
    from azure.iot.device import IoTHubDeviceClient, Message
    AZURE_AVAILABLE = True
except ImportError:
    print("Azure IoT SDK not installed - testing with mock")
    AZURE_AVAILABLE = False
    
    # Create mock classes for testing
    class Message:
        def __init__(self, data):
            self.data = data
            self.content_type = None
            self.content_encoding = None
            self.custom_properties = {}
    
    class IoTHubDeviceClient:
        @staticmethod
        def create_from_connection_string(conn_str):
            return MockClient()
    
    class MockClient:
        def connect(self):
            print("[MOCK] Connected to Azure IoT Hub")
        
        def disconnect(self):
            print("[MOCK] Disconnected from Azure IoT Hub")
        
        def send_message(self, message):
            print(f"[MOCK] Sending message:")
            print(f"  Content-Type: {message.content_type}")
            print(f"  Content-Encoding: {message.content_encoding}")
            print(f"  Custom Properties: {message.custom_properties}")
            data = json.loads(message.data)
            print(f"  Payload: {json.dumps(data, indent=2)}")
            print()
    
    # Inject mocks
    sys.modules['azure.iot.device'] = type('module', (), {
        'IoTHubDeviceClient': IoTHubDeviceClient,
        'Message': Message
    })()

# Now import the reporter (will use real or mock Azure SDK)
from azure_iot_reporter import AzureIoTReporter, is_azure_iot_available

def test_azure_reporter():
    """Test Azure IoT reporter functionality"""
    print("=" * 60)
    print("Azure IoT Reporter Test")
    print("=" * 60)
    print()
    
    # Test availability check
    print(f"Azure IoT SDK available: {is_azure_iot_available()}")
    print()
    
    # Create reporter with mock connection string
    mock_connection = "HostName=test-hub.azure-devices.net;DeviceId=test-device;SharedAccessKey=dGVzdGtleQ=="
    reporter = AzureIoTReporter(mock_connection, device_id="test-dwm3001cdk")
    
    print("1. Testing connection...")
    reporter.connect()
    print()
    
    print("2. Testing status message...")
    reporter.send_status("online", {
        "beacon1_position": [0.0, 0.0],
        "beacon2_position": [1.0, 0.0],
        "averaging_window": 2.0
    })
    
    print("3. Testing position data...")
    reporter.send_position_data(
        x=1.234,
        y=0.567,
        dist1=1.403,
        dist2=1.313,
        measurement_count1=82,
        measurement_count2=82
    )
    
    print("4. Testing distance measurement...")
    reporter.send_distance_measurements(
        beacon_num=1,
        distance=1.403,
        measurement_count=82
    )
    
    print("5. Testing offline status...")
    reporter.send_status("offline")
    
    print("6. Testing disconnection...")
    reporter.disconnect()
    print()
    
    print("=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    test_azure_reporter()
