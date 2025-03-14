"""
InfluxDB client for storing and retrieving metrics
"""
import logging
import datetime
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Configure logging
logger = logging.getLogger("utils.influx")

class InfluxClient:
    """Client for interacting with InfluxDB"""
    
    def __init__(self, host='influxdb', port=8086, token='ChangeThisPassword', org='my-org', bucket='my-bucket'):
        """Initialize the InfluxDB client"""
        self.host = host
        self.port = port
        self.token = token
        self.org = org
        self.bucket = bucket
        self.url = f"http://{host}:{port}"
        
        # Create client
        self.client = None
        self.write_api = None
        self.query_api = None
        
        # Try to connect
        self._connect()
    
    def _connect(self):
        """Connect to InfluxDB"""
        try:
            self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            logger.info(f"Connected to InfluxDB at {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {str(e)}")
            self.client = None
            self.write_api = None
            self.query_api = None
    
    def write_data(self, data):
        """
        Write metrics to InfluxDB
        
        Args:
            data: List of data points to write
        """
        if not self.write_api:
            logger.error("Cannot write data: InfluxDB client not connected")
            self._connect()
            if not self.write_api:
                return False
        
        try:
            self.write_api.write(bucket=self.bucket, record=data)
            return True
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {str(e)}")
            # Try to reconnect
            self._connect()
            return False
    
    def query(self, query):
        """
        Execute a Flux query against InfluxDB
        
        Args:
            query: Flux query string
            
        Returns:
            Query result or None if failed
        """
        if not self.query_api:
            logger.error("Cannot query data: InfluxDB client not connected")
            self._connect()
            if not self.query_api:
                return None
        
        try:
            result = self.query_api.query(query=query, org=self.org)
            return result
        except Exception as e:
            logger.error(f"Error querying InfluxDB: {str(e)}")
            # Try to reconnect
            self._connect()
            return None
    
    def get_device_status(self):
        """
        Get the current status of all monitored devices
        
        Returns:
            List of devices with their status
        """
        # Query system metrics for each device to determine status
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "system_metrics")
            |> filter(fn: (r) => r._field == "cpu_load" or r._field == "memory_usage")
            |> last()
            |> group(columns: ["device_id", "device_name", "device_type"])
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            # Process result
            devices = {}
            for table in result:
                for record in table.records:
                    device_id = record.values.get('device_id')
                    if device_id not in devices:
                        devices[device_id] = {
                            'id': device_id,
                            'name': record.values.get('device_name'),
                            'type': record.values.get('device_type'),
                            'status': 'online',
                            'last_seen': record.values.get('_time'),
                            'metrics': {}
                        }
                    
                    field = record.values.get('_field')
                    value = record.values.get('_value')
                    devices[device_id]['metrics'][field] = value
            
            return list(devices.values())
        except Exception as e:
            logger.error(f"Error getting device status: {str(e)}")
            return []
    
    def get_devices(self):
        """
        Get the list of all monitored devices
        
        Returns:
            List of devices
        """
        # Query to get unique devices
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "system_metrics")
            |> group(columns: ["device_id", "device_name", "device_type"])
            |> limit(n: 1)
            |> yield(name: "devices")
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            # Process result
            devices = {}
            for table in result:
                for record in table.records:
                    device_id = record.values.get('device_id')
                    if device_id not in devices:
                        devices[device_id] = {
                            'id': device_id,
                            'name': record.values.get('device_name'),
                            'type': record.values.get('device_type')
                        }
            
            return list(devices.values())
        except Exception as e:
            logger.error(f"Error getting device list: {str(e)}")
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
        # Build measurement filter based on metric type
        measurement_filter = ''
        if metric_type == 'all':
            measurement_filter = 'r._measurement == "system_metrics" or r._measurement == "interface_metrics"'
        elif metric_type == 'cpu':
            measurement_filter = 'r._measurement == "system_metrics" and r._field == "cpu_load"'
        elif metric_type == 'memory':
            measurement_filter = 'r._measurement == "system_metrics" and r._field == "memory_usage"'
        elif metric_type == 'interface':
            measurement_filter = 'r._measurement == "interface_metrics"'
        else:
            measurement_filter = f'r._measurement == "{metric_type}"'
        
        # Query to get metrics
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {start_time}, stop: {end_time})
            |> filter(fn: (r) => {measurement_filter})
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> group(columns: ["_measurement", "_field"])
            |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)
        '''
        
        try:
            result = self.query(query)
            if not result:
                return {}
            
            # Process result
            metrics = {
                'device_id': device_id,
                'data': {}
            }
            
            for table in result:
                measurement = table.records[0].values.get('_measurement')
                field = table.records[0].values.get('_field')
                
                if measurement not in metrics['data']:
                    metrics['data'][measurement] = {}
                
                if field not in metrics['data'][measurement]:
                    metrics['data'][measurement][field] = []
                
                for record in table.records:
                    metrics['data'][measurement][field].append({
                        'time': record.values.get('_time').strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'value': record.values.get('_value')
                    })
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting device metrics: {str(e)}")
            return {}
    
    def get_device_interfaces(self, device_id):
        """
        Get interface information for a specific device
        
        Args:
            device_id: ID of the device
            
        Returns:
            List of interfaces
        """
        # Query to get interfaces
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "interface_metrics")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> group(columns: ["interface"])
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            # Process result
            interfaces = {}
            for table in result:
                for record in table.records:
                    interface = record.values.get('interface')
                    if interface not in interfaces:
                        interfaces[interface] = {
                            'name': interface,
                            'status': 'down',
                            'rx_bytes': 0,
                            'tx_bytes': 0
                        }
                    
                    field = record.values.get('_field')
                    value = record.values.get('_value')
                    
                    if field == 'status' and value == 1:
                        interfaces[interface]['status'] = 'up'
                    elif field == 'rx_bytes':
                        interfaces[interface]['rx_bytes'] = value
                    elif field == 'tx_bytes':
                        interfaces[interface]['tx_bytes'] = value
            
            return list(interfaces.values())
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
        # Query to get wireless interfaces
        interfaces_query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "wireless_interface")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> group(columns: ["interface"])
            |> last()
        '''
        
        # Query to get wireless clients
        clients_query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "wireless_client")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> group(columns: ["mac_address"])
            |> last()
        '''
        
        try:
            # Get wireless interfaces
            interfaces_result = self.query(interfaces_query)
            interfaces = {}
            
            if interfaces_result:
                for table in interfaces_result:
                    for record in table.records:
                        interface = record.values.get('interface')
                        if interface not in interfaces:
                            interfaces[interface] = {
                                'name': interface,
                                'ssid': record.values.get('ssid', ''),
                                'mac_address': record.values.get('mac_address', ''),
                                'band': record.values.get('band', ''),
                                'mode': record.values.get('mode', ''),
                                'frequency': 0,
                                'tx_power': 0,
                                'status': 'down',
                                'clients': []
                            }
                        
                        field = record.values.get('_field')
                        value = record.values.get('_value')
                        
                        if field == 'frequency':
                            interfaces[interface]['frequency'] = value
                        elif field == 'tx_power':
                            interfaces[interface]['tx_power'] = value
                        elif field == 'status' and value == 1:
                            interfaces[interface]['status'] = 'up'
            
            # Get wireless clients
            clients_result = self.query(clients_query)
            clients = {}
            
            if clients_result:
                for table in clients_result:
                    for record in table.records:
                        mac_address = record.values.get('mac_address')
                        interface = record.values.get('interface')
                        
                        if interface in interfaces and mac_address not in clients:
                            client = {
                                'mac_address': mac_address,
                                'interface': interface,
                                'signal_strength': 0,
                                'signal_to_noise': 0,
                                'tx_rate': 0,
                                'rx_rate': 0,
                                'uptime_seconds': 0
                            }
                            
                            field = record.values.get('_field')
                            value = record.values.get('_value')
                            
                            if field == 'signal_strength':
                                client['signal_strength'] = value
                            elif field == 'signal_to_noise':
                                client['signal_to_noise'] = value
                            elif field == 'tx_rate':
                                client['tx_rate'] = value
                            elif field == 'rx_rate':
                                client['rx_rate'] = value
                            elif field == 'uptime_seconds':
                                client['uptime_seconds'] = value
                            
                            clients[mac_address] = client
                            interfaces[interface]['clients'].append(client)
            
            return {
                'device_id': device_id,
                'interfaces': list(interfaces.values()),
                'client_count': len(clients)
            }
        except Exception as e:
            logger.error(f"Error getting wireless metrics: {str(e)}")
            return {
                'device_id': device_id,
                'interfaces': [],
                'client_count': 0
            }
    
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
        # Query to get QoS queues
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -5m)
            |> filter(fn: (r) => r._measurement == "qos_queue")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> group(columns: ["queue_name"])
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return {'device_id': device_id, 'queues': []}
            
            # Process result
            queues = {}
            for table in result:
                for record in table.records:
                    queue_name = record.values.get('queue_name')
                    if queue_name not in queues:
                        queues[queue_name] = {
                            'name': queue_name,
                            'target': record.values.get('target', ''),
                            'parent': record.values.get('parent', ''),
                            'priority': record.values.get('priority', 8),
                            'max_limit': {'download': 0, 'upload': 0},
                            'limit_at': {'download': 0, 'upload': 0},
                            'disabled': False
                        }
                    
                    field = record.values.get('_field')
                    value = record.values.get('_value')
                    
                    if field == 'max_limit_download':
                        queues[queue_name]['max_limit']['download'] = value
                    elif field == 'max_limit_upload':
                        queues[queue_name]['max_limit']['upload'] = value
                    elif field == 'limit_at_download':
                        queues[queue_name]['limit_at']['download'] = value
                    elif field == 'limit_at_upload':
                        queues[queue_name]['limit_at']['upload'] = value
                    elif field == 'disabled' and value == 1:
                        queues[queue_name]['disabled'] = True
            
            return {
                'device_id': device_id,
                'queues': list(queues.values())
            }
        except Exception as e:
            logger.error(f"Error getting QoS metrics: {str(e)}")
            return {
                'device_id': device_id,
                'queues': []
            }
    
    def get_alerts(self):
        """
        Get active alerts
        
        Returns:
            List of active alerts
        """
        # Query to get alerts
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "alerts")
            |> filter(fn: (r) => r.active == true)
            |> group(columns: ["alert_id"])
            |> last()
        '''
        
        try:
            result = self.query(query)
            if not result:
                return []
            
            # Process result
            alerts = []
            for table in result:
                for record in table.records:
                    alerts.append({
                        'id': record.values.get('alert_id'),
                        'type': record.values.get('type'),
                        'device_id': record.values.get('device_id'),
                        'device_name': record.values.get('device_name'),
                        'message': record.values.get('message'),
                        'value': record.values.get('value'),
                        'threshold': record.values.get('threshold'),
                        'timestamp': record.values.get('_time').strftime('%Y-%m-%dT%H:%M:%SZ')
                    })
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {str(e)}")
            return []
