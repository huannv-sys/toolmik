"""
InfluxDB client for storing and retrieving metrics
"""
import logging
import time
from typing import Dict, List, Optional, Any, Union
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger('utils.influx')

class InfluxClient:
    """Client for interacting with InfluxDB"""
    
    def __init__(self, host='localhost', port=8086, token='ChangeThisPassword', org='my-org', bucket='my-bucket'):
        """Initialize the InfluxDB client"""
        self.host = host
        self.port = port
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = None
        self.write_api = None
        self.query_api = None
        self._connect()
    
    def _connect(self):
        """Connect to InfluxDB"""
        try:
            url = f"http://{self.host}:{self.port}"
            self.client = InfluxDBClient(url=url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            logger.info(f"Connected to InfluxDB at {url}")
        except Exception as e:
            logger.error(f"Error connecting to InfluxDB: {str(e)}")
            raise
    
    def write_data(self, data):
        """
        Write metrics to InfluxDB
        
        Args:
            data: List of data points to write
        """
        try:
            self.write_api.write(bucket=self.bucket, record=data)
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {str(e)}")
    
    def query(self, query):
        """
        Execute a Flux query against InfluxDB
        
        Args:
            query: Flux query string
            
        Returns:
            Query result or None if failed
        """
        try:
            return self.query_api.query(query=query, org=self.org)
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {str(e)}")
            return None
    
    def get_device_status(self):
        """
        Get the current status of all monitored devices
        
        Returns:
            List of devices with their status
        """
        # Query to get the latest status of all devices
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "device_status")
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            devices = []
            for table in result:
                for record in table.records:
                    devices.append({
                        'device_id': record.values.get('device_id', 'unknown'),
                        'status': record.values.get('_value', 'unknown'),
                        'last_seen': record.values.get('_time', 'unknown')
                    })
            
            return devices
        except Exception as e:
            logger.error(f"Error getting device status: {str(e)}")
            return []
    
    def get_devices(self):
        """
        Get the list of all monitored devices
        
        Returns:
            List of devices
        """
        # Query to get all unique device IDs
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "device" or r._measurement == "interface" or r._measurement == "wireless")
            |> group(columns: ["device_id"])
            |> distinct(column: "device_id")
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            devices = []
            for table in result:
                for record in table.records:
                    device_id = record.values.get('_value', '')
                    if device_id and device_id not in [d.get('id') for d in devices]:
                        devices.append({
                            'id': device_id,
                            'name': device_id,  # In a real scenario, we'd have a mapping of IDs to names
                            'type': 'unknown'   # In a real scenario, we'd have device types
                        })
            
            return devices
        except Exception as e:
            logger.error(f"Error getting devices: {str(e)}")
            return []
    
    def get_device_metrics(self, device_id, metric_type='all', start_time='-1h', end_time='now()'):
        """
        Get metrics for a specific device
        
        Args:
            device_id: ID of the device
            metric_type: Type of metrics to get (all, cpu, memory, etc.)
            start_time: Start time for data range
            end_time: End time for data range
            
        Returns:
            Dictionary with metrics
        """
        metrics = {}
        
        # Define queries based on metric type
        if metric_type == 'all' or metric_type == 'cpu':
            cpu_query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {start_time}, stop: {end_time})
                |> filter(fn: (r) => r._measurement == "device" and r.device_id == "{device_id}" and r._field == "cpu_load")
                |> aggregateWindow(every: 5m, fn: mean)
            '''
            
            try:
                result = self.query(cpu_query)
                if result:
                    cpu_data = []
                    for table in result:
                        for record in table.records:
                            cpu_data.append({
                                'time': record.values.get('_time'),
                                'value': record.values.get('_value', 0)
                            })
                    
                    metrics['cpu'] = cpu_data
            except Exception as e:
                logger.error(f"Error getting CPU metrics: {str(e)}")
        
        if metric_type == 'all' or metric_type == 'memory':
            memory_query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: {start_time}, stop: {end_time})
                |> filter(fn: (r) => r._measurement == "device" and r.device_id == "{device_id}" and r._field == "memory_used")
                |> aggregateWindow(every: 5m, fn: mean)
            '''
            
            try:
                result = self.query(memory_query)
                if result:
                    memory_data = []
                    for table in result:
                        for record in table.records:
                            memory_data.append({
                                'time': record.values.get('_time'),
                                'value': record.values.get('_value', 0)
                            })
                    
                    metrics['memory'] = memory_data
            except Exception as e:
                logger.error(f"Error getting memory metrics: {str(e)}")
        
        # Add more metric types as needed
        
        return metrics
    
    def get_device_interfaces(self, device_id):
        """
        Get interface information for a specific device
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of interfaces
        """
        # Query to get the latest interface metrics
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "interface" and r.device_id == "{device_id}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> group(columns: ["interface_name"])
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            interfaces = []
            for table in result:
                for record in table.records:
                    interfaces.append({
                        'name': record.values.get('interface_name', 'unknown'),
                        'type': record.values.get('type', 'unknown'),
                        'status': record.values.get('status', 'down'),
                        'rx_bytes': record.values.get('rx_bytes', 0),
                        'tx_bytes': record.values.get('tx_bytes', 0),
                        'rx_packets': record.values.get('rx_packets', 0),
                        'tx_packets': record.values.get('tx_packets', 0),
                        'errors': record.values.get('errors', 0)
                    })
            
            return interfaces
        except Exception as e:
            logger.error(f"Error getting device interfaces: {str(e)}")
            return []
    
    def get_wireless_metrics(self, device_id, start_time='-1h', end_time='now()'):
        """
        Get wireless metrics for a specific device
        
        Args:
            device_id: ID of the device
            start_time: Start time for data range
            end_time: End time for data range
            
        Returns:
            Dictionary with wireless metrics
        """
        # Query to get the latest wireless interface metrics
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time}, stop: {end_time})
            |> filter(fn: (r) => r._measurement == "wireless" and r.device_id == "{device_id}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> group(columns: ["interface_name"])
        '''
        
        try:
            result = self.query(query)
            if not result:
                return {'interfaces': [], 'clients': []}
            
            interfaces = []
            clients = []
            
            for table in result:
                for record in table.records:
                    # Check if this is an interface or client record
                    record_type = record.values.get('type', '')
                    
                    if record_type == 'interface':
                        interfaces.append({
                            'name': record.values.get('interface_name', 'unknown'),
                            'ssid': record.values.get('ssid', 'unknown'),
                            'frequency': record.values.get('frequency', 0),
                            'channel': record.values.get('channel', 0),
                            'tx_power': record.values.get('tx_power', 0),
                            'clients': record.values.get('client_count', 0),
                            'time': record.values.get('_time')
                        })
                    elif record_type == 'client':
                        clients.append({
                            'mac': record.values.get('client_mac', 'unknown'),
                            'interface': record.values.get('interface_name', 'unknown'),
                            'signal': record.values.get('signal', 0),
                            'tx_rate': record.values.get('tx_rate', 0),
                            'rx_rate': record.values.get('rx_rate', 0),
                            'time': record.values.get('_time')
                        })
            
            return {
                'interfaces': interfaces,
                'clients': clients
            }
        except Exception as e:
            logger.error(f"Error getting wireless metrics: {str(e)}")
            return {'interfaces': [], 'clients': []}
    
    def get_qos_metrics(self, device_id, start_time='-1h', end_time='now()'):
        """
        Get QoS metrics for a specific device
        
        Args:
            device_id: ID of the device
            start_time: Start time for data range
            end_time: End time for data range
            
        Returns:
            Dictionary with QoS metrics
        """
        # Query to get QoS metrics
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time}, stop: {end_time})
            |> filter(fn: (r) => r._measurement == "qos" and r.device_id == "{device_id}")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> group(columns: ["queue_name"])
        '''
        
        try:
            result = self.query(query)
            if not result:
                return {'queues': []}
            
            queues = []
            
            for table in result:
                for record in table.records:
                    queues.append({
                        'name': record.values.get('queue_name', 'unknown'),
                        'target': record.values.get('target', 'unknown'),
                        'limit_up': record.values.get('limit_up', 0),
                        'limit_down': record.values.get('limit_down', 0),
                        'current_up': record.values.get('current_up', 0),
                        'current_down': record.values.get('current_down', 0),
                        'time': record.values.get('_time')
                    })
            
            return {'queues': queues}
        except Exception as e:
            logger.error(f"Error getting QoS metrics: {str(e)}")
            return {'queues': []}
    
    def get_alerts(self):
        """
        Get active alerts
        
        Returns:
            List of active alerts
        """
        # Query to get active alerts
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -24h)
            |> filter(fn: (r) => r._measurement == "alert" and r.active == "true")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> group(columns: ["alert_id"])
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            alerts = []
            
            for table in result:
                for record in table.records:
                    alerts.append({
                        'id': record.values.get('alert_id', 'unknown'),
                        'type': record.values.get('type', 'unknown'),
                        'device_id': record.values.get('device_id', 'unknown'),
                        'message': record.values.get('message', ''),
                        'value': record.values.get('value', 0),
                        'threshold': record.values.get('threshold', 0),
                        'resource': record.values.get('resource', ''),
                        'time': record.values.get('_time')
                    })
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []