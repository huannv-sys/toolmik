"""
QoS collector module
Collects Quality of Service metrics from MikroTik devices
"""
import time
import logging
from . import BaseCollector
from utils.influx import InfluxClient

# Optional: Use librouteros if available
try:
    import librouteros
    HAVE_ROUTEROS = True
except ImportError:
    HAVE_ROUTEROS = False
    logging.warning("librouteros not available, QoS monitoring may be limited")

# Try to import SNMP libraries
try:
    import pysnmp.hlapi as snmp
    HAVE_SNMP = True
except ImportError:
    HAVE_SNMP = False
    logging.warning("pysnmp not available, QoS monitoring may be limited")

# Configure logging
logger = logging.getLogger("collectors.qos")

class Collector(BaseCollector):
    """Collector for QoS metrics"""
    
    def __init__(self, config):
        """Initialize QoS collector"""
        self.interval = 60  # Collect every 60 seconds
        self.devices = []  # Will be populated in initialize()
        self.influx = None
        super().__init__(config)
    
    def initialize(self):
        """Initialize collector resources"""
        # Create InfluxDB client
        influx_config = self.config.get('influxdb', {})
        self.influx = InfluxClient(
            host=influx_config.get('host', 'localhost'),
            port=influx_config.get('port', 8086),
            token=influx_config.get('token', 'YM_NhDux0lCLYdPjyypSDQzAtATgFUh3x38CPDB34CzW51AXE1H2Zj9Gvqh7OhzWm9tF6jFKBcdNS4jn72FgFw=='),
            org=influx_config.get('org', 'my-org'),
            bucket=influx_config.get('bucket', 'my-bucket')
        )
        
        # Load device list (in a real application, this would come from a database)
        # For demo purposes, we'll hardcode a test device
        self.devices = [
            {
                'id': 'mikrotik1',
                'name': 'Main Router',
                'host': '192.168.1.1',
                'type': 'mikrotik',
                'snmp_community': 'public',
                'api_user': 'admin',
                'api_password': 'password',
                'use_api': HAVE_ROUTEROS
            }
        ]
        
        logger.info(f"Initialized QoS collector with {len(self.devices)} devices")
    
    def collect(self):
        """Collect QoS metrics from all devices"""
        start_time = time.time()
        logger.debug("Starting QoS metrics collection")
        
        for device in self.devices:
            try:
                if device.get('type') == 'mikrotik':
                    if device.get('use_api', False) and HAVE_ROUTEROS:
                        self._collect_mikrotik_api(device)
                    elif HAVE_SNMP:
                        self._collect_mikrotik_snmp(device)
                    else:
                        logger.warning(f"No collection method available for device {device['id']}")
                # Add support for other device types as needed
            except Exception as e:
                logger.error(f"Error collecting QoS metrics for device {device['id']}: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.debug(f"Completed QoS metrics collection in {elapsed:.2f} seconds")
    
    def _collect_mikrotik_api(self, device):
        """Collect QoS metrics using MikroTik API"""
        try:
            # Connect to RouterOS API
            api = librouteros.connect(
                host=device['host'],
                username=device['api_user'],
                password=device['api_password']
            )
            
            # Collect queue metrics
            simple_queues = api.path('/queue/simple').get()
            
            # Process queue metrics
            queue_metrics = []
            for queue in simple_queues:
                queue_metrics.append({
                    'name': queue.get('name', 'unknown'),
                    'target': queue.get('target', ''),
                    'parent': queue.get('parent', ''),
                    'max_limit': self._parse_limit(queue.get('max-limit', '0/0')),
                    'limit_at': self._parse_limit(queue.get('limit-at', '0/0')),
                    'priority': int(queue.get('priority', 8)),
                    'disabled': queue.get('disabled', False)
                })
            
            # Collect queue stats (not directly available in API,
            # but can be accessed via traffic monitoring in a real implementation)
            
            # Store metrics in InfluxDB
            self._store_queue_metrics(device, queue_metrics)
            
        except Exception as e:
            logger.error(f"API collection error for device {device['id']}: {str(e)}")
            raise
    
    def _collect_mikrotik_snmp(self, device):
        """Collect QoS metrics using SNMP"""
        try:
            # SNMP connection parameters
            host = device['host']
            community = device.get('snmp_community', 'public')
            
            # In a real implementation, we would perform SNMP walks to collect
            # queue information and statistics
            
            # For demonstration purposes, mocking with sample data
            queue_metrics = [
                {
                    'name': 'Internet',
                    'target': '192.168.1.0/24',
                    'parent': 'none',
                    'max_limit': {'download': 10000000, 'upload': 5000000},  # 10/5 Mbps
                    'limit_at': {'download': 5000000, 'upload': 2500000},    # 5/2.5 Mbps
                    'priority': 5,
                    'disabled': False
                },
                {
                    'name': 'VoIP',
                    'target': '192.168.1.10',
                    'parent': 'none',
                    'max_limit': {'download': 1000000, 'upload': 1000000},   # 1/1 Mbps
                    'limit_at': {'download': 1000000, 'upload': 1000000},    # 1/1 Mbps
                    'priority': 1,
                    'disabled': False
                }
            ]
            
            # Store metrics in InfluxDB
            self._store_queue_metrics(device, queue_metrics)
            
        except Exception as e:
            logger.error(f"SNMP collection error for device {device['id']}: {str(e)}")
            raise
    
    def _parse_limit(self, limit_str):
        """
        Parse MikroTik bandwidth limit string (e.g., "10M/5M")
        Returns a dict with download and upload values in bps
        """
        try:
            if '/' in limit_str:
                download, upload = limit_str.split('/')
            else:
                download = upload = limit_str
                
            return {
                'download': self._convert_to_bps(download),
                'upload': self._convert_to_bps(upload)
            }
        except:
            return {'download': 0, 'upload': 0}
    
    def _convert_to_bps(self, value_str):
        """
        Convert MikroTik bandwidth value to bps (bits per second)
        Handles values like "10M", "1G", etc.
        """
        if not value_str or value_str == '0':
            return 0
            
        try:
            # Remove any non-numeric suffix
            numeric_part = ''
            unit_part = ''
            
            for char in value_str:
                if char.isdigit() or char == '.':
                    numeric_part += char
                else:
                    unit_part += char
            
            value = float(numeric_part)
            
            # Convert based on unit
            unit = unit_part.upper()
            if unit == 'K':
                return int(value * 1000)
            elif unit == 'M':
                return int(value * 1000000)
            elif unit == 'G':
                return int(value * 1000000000)
            else:
                return int(value)
        except:
            return 0
    
    def _store_queue_metrics(self, device, queues):
        """Store QoS queue metrics in InfluxDB"""
        data = []
        
        for queue in queues:
            data.append({
                "measurement": "qos_queue",
                "tags": {
                    "device_id": device['id'],
                    "device_name": device['name'],
                    "queue_name": queue['name'],
                    "target": queue['target'],
                    "parent": queue['parent'],
                    "priority": queue['priority']
                },
                "fields": {
                    "max_limit_download": float(queue['max_limit']['download']),
                    "max_limit_upload": float(queue['max_limit']['upload']),
                    "limit_at_download": float(queue['limit_at']['download']),
                    "limit_at_upload": float(queue['limit_at']['upload']),
                    "disabled": 1 if queue['disabled'] else 0
                }
            })
        
        self.influx.write_data(data)
        logger.debug(f"Stored QoS queue metrics for device {device['id']}")
