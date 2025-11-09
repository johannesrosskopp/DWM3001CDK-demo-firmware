#!/usr/bin/env python3
"""
Azure IoT Hub Reporter for DWM3001CDK Positioning System

Sends positioning data and distance measurements to Azure IoT Hub.
"""

import json
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from azure.iot.device import IoTHubDeviceClient, Message
    AZURE_IOT_AVAILABLE = True
except ImportError:
    AZURE_IOT_AVAILABLE = False
    logging.warning("Azure IoT SDK not available. Install with: pip install azure-iot-device")


class AzureIoTReporter:
    """Reports positioning data to Azure IoT Hub"""
    
    def __init__(self, connection_string: str, device_id: str = "dwm3001cdk-tag"):
        """
        Initialize Azure IoT Hub reporter
        
        Args:
            connection_string: Azure IoT Hub device connection string
            device_id: Device identifier for telemetry
        """
        if not AZURE_IOT_AVAILABLE:
            raise ImportError("Azure IoT SDK not installed. Run: pip install azure-iot-device")
        
        self.device_id = device_id
        self.connection_string = connection_string
        self.client = None
        self.connected = False
        self.message_count = 0
        
    def connect(self):
        """Connect to Azure IoT Hub"""
        try:
            logging.info(f"Connecting to Azure IoT Hub as device: {self.device_id}")
            self.client = IoTHubDeviceClient.create_from_connection_string(self.connection_string)
            self.client.connect()
            self.connected = True
            logging.info("Successfully connected to Azure IoT Hub")
        except Exception as e:
            logging.error(f"Failed to connect to Azure IoT Hub: {e}")
            self.connected = False
            raise
    
    def disconnect(self):
        """Disconnect from Azure IoT Hub"""
        if self.client and self.connected:
            try:
                self.client.disconnect()
                self.connected = False
                logging.info("Disconnected from Azure IoT Hub")
            except Exception as e:
                logging.error(f"Error disconnecting from Azure IoT Hub: {e}")
    
    def send_position_data(self, 
                          x: float, 
                          y: float, 
                          dist1: float, 
                          dist2: float,
                          measurement_count1: int,
                          measurement_count2: int) -> bool:
        """
        Send position and distance data to Azure IoT Hub
        
        Args:
            x: X coordinate in meters
            y: Y coordinate in meters
            dist1: Distance to beacon 1 in meters
            dist2: Distance to beacon 2 in meters
            measurement_count1: Number of measurements for beacon 1
            measurement_count2: Number of measurements for beacon 2
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected:
            logging.warning("Not connected to Azure IoT Hub, cannot send data")
            return False
        
        try:
            # Prepare telemetry payload
            telemetry = {
                "deviceId": self.device_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "position": {
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "unit": "meters"
                },
                "distances": {
                    "beacon1": {
                        "distance": round(dist1, 3),
                        "measurementCount": measurement_count1
                    },
                    "beacon2": {
                        "distance": round(dist2, 3),
                        "measurementCount": measurement_count2
                    }
                },
                "messageId": self.message_count
            }
            
            # Create IoT Hub message
            message = Message(json.dumps(telemetry))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"
            
            # Add custom properties
            message.custom_properties["messageType"] = "positioning"
            message.custom_properties["deviceType"] = "DWM3001CDK"
            
            # Send message
            self.client.send_message(message)
            self.message_count += 1
            
            logging.debug(f"Sent position data to Azure IoT Hub (message #{self.message_count})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send data to Azure IoT Hub: {e}")
            return False
    
    def send_distance_measurements(self,
                                   beacon_num: int,
                                   distance: float,
                                   measurement_count: int) -> bool:
        """
        Send individual distance measurement to Azure IoT Hub
        
        Args:
            beacon_num: Beacon number (1 or 2)
            distance: Distance in meters
            measurement_count: Number of measurements averaged
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected:
            logging.warning("Not connected to Azure IoT Hub, cannot send data")
            return False
        
        try:
            telemetry = {
                "deviceId": self.device_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "beaconNumber": beacon_num,
                "distance": round(distance, 3),
                "measurementCount": measurement_count,
                "unit": "meters",
                "messageId": self.message_count
            }
            
            message = Message(json.dumps(telemetry))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"
            message.custom_properties["messageType"] = "distance"
            message.custom_properties["deviceType"] = "DWM3001CDK"
            
            self.client.send_message(message)
            self.message_count += 1
            
            logging.debug(f"Sent distance measurement to Azure IoT Hub (beacon {beacon_num})")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send distance measurement to Azure IoT Hub: {e}")
            return False
    
    def send_status(self, status: str, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Send device status to Azure IoT Hub
        
        Args:
            status: Status message (e.g., "online", "offline", "error")
            details: Optional additional details
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            telemetry = {
                "deviceId": self.device_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": status,
                "details": details or {},
                "messageId": self.message_count
            }
            
            message = Message(json.dumps(telemetry))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"
            message.custom_properties["messageType"] = "status"
            message.custom_properties["deviceType"] = "DWM3001CDK"
            
            self.client.send_message(message)
            self.message_count += 1
            
            logging.debug(f"Sent status to Azure IoT Hub: {status}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send status to Azure IoT Hub: {e}")
            return False


def is_azure_iot_available() -> bool:
    """Check if Azure IoT SDK is available"""
    return AZURE_IOT_AVAILABLE
