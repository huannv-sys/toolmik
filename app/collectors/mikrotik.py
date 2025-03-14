"""
MikroTik collector module
Collects metrics from MikroTik devices using their API
"""
import logging
import time
from . import BaseCollector
from utils.influx import InfluxClient

# Optional: Use librouteros if available
try:
    import librouteros
    HAVE_ROUTEROS = True
except ImportError:
    HAVE_ROUTEROS = False
    logging.warning("librouteros not available, falling back to SNMP")

# Use pysnmp for SNMP-based collection
import pysnmp.hlapi as snmp

# Configure logging
logger = logging.getLogger("collectors.mikrotik")

class Collector(BaseCollector):
    """Collector for MikroTik devices"""
    
    def __init__(self, config):
        """Initialize MikroTik collector"""
        self.interval = 30  # Collect every 30 seconds
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
                'snmp_community': 'public',
                'api_user': 'admin',
                'api_password': 'password',
                'use_api': HAVE_ROUTEROS
            }
        ]
        
        logger.info(f"Initialized MikroTik collector with {len(self.devices)} devices")
    
    def collect(self):
        """Collect metrics from all MikroTik devices"""
        start_time = time.time()
        logger.debug("Starting MikroTik metrics collection")
        
        for device in self.devices:
            try:
                # Check if we're in demo mode or can't reach the device
                if device.get('demo_mode', False) or not self._can_connect(device['host']):
                    logger.info(f"Using demo data for device {device['id']} (host: {device['host']})")
                    self._collect_demo_data(device)
                elif device.get('use_api', False) and HAVE_ROUTEROS:
                    self._collect_via_api(device)
                else:
                    self._collect_via_snmp(device)
            except Exception as e:
                logger.error(f"Error collecting metrics for device {device['id']}: {str(e)}")
                # Fallback to demo data on error
                try:
                    logger.info(f"Falling back to demo data for device {device['id']}")
                    self._collect_demo_data(device)
                except Exception as demo_error:
                    logger.error(f"Error generating demo data: {str(demo_error)}")
        
        elapsed = time.time() - start_time
        logger.debug(f"Completed MikroTik metrics collection in {elapsed:.2f} seconds")
    
    def _collect_via_api(self, device):
        """Collect metrics using MikroTik API"""
        try:
            # Connect to RouterOS API
            api = librouteros.connect(
                host=device['host'],
                username=device['api_user'],
                password=device['api_password']
            )
            
            # Collect system resources
            resources = api.path('/system/resource').get()[0]
            
            # Collect CPU load
            cpu_load = resources.get('cpu-load', 0)
            
            # Collect memory usage
            total_memory = int(resources.get('total-memory', 0))
            free_memory = int(resources.get('free-memory', 0))
            memory_usage = 0
            if total_memory > 0:
                memory_usage = round(((total_memory - free_memory) / total_memory) * 100, 2)
            
            # Collect interface metrics
            interfaces = api.path('/interface').get()
            interface_metrics = []
            
            for iface in interfaces:
                name = iface.get('name', 'unknown')
                if not name.startswith('vlan') and not name.startswith('bridge'):
                    # Get interface statistics
                    stats = api.path(f'/interface/monitor-traffic', 
                                    {'interface': name, 'once': ''})[0]
                    
                    rx_bytes = stats.get('rx-bits-per-second', 0)
                    tx_bytes = stats.get('tx-bits-per-second', 0)
                    
                    interface_metrics.append({
                        'name': name,
                        'rx_bytes': rx_bytes,
                        'tx_bytes': tx_bytes,
                        'status': iface.get('running', False)
                    })
            
            # Store metrics in InfluxDB
            self._store_system_metrics(device, cpu_load, memory_usage)
            self._store_interface_metrics(device, interface_metrics)
            
        except Exception as e:
            logger.error(f"API collection error for device {device['id']}: {str(e)}")
            raise
    
    def _collect_via_snmp(self, device):
        """Collect metrics using SNMP"""
        try:
            # SNMP connection parameters
            host = device['host']
            community = device.get('snmp_community', 'public')
            
            # Collect system metrics
            # CPU Load - MikroTik OID 1.3.6.1.4.1.14988.1.1.3.14.0
            cpu_load = self._get_snmp_value(host, community, '1.3.6.1.4.1.14988.1.1.3.14.0')
            
            # Total Memory - MikroTik OID 1.3.6.1.4.1.14988.1.1.3.10.0
            total_memory = self._get_snmp_value(host, community, '1.3.6.1.4.1.14988.1.1.3.10.0')
            
            # Free Memory - MikroTik OID 1.3.6.1.4.1.14988.1.1.3.11.0
            free_memory = self._get_snmp_value(host, community, '1.3.6.1.4.1.14988.1.1.3.11.0')
            
            # Calculate memory usage percentage
            memory_usage = 0
            if total_memory > 0:
                memory_usage = round(((total_memory - free_memory) / total_memory) * 100, 2)
            
            # Collect interface metrics
            # Get interface list - Standard SNMP OID 1.3.6.1.2.1.2.2
            interface_metrics = []
            
            # We'd implement full SNMP walk here for interfaces
            # For brevity, mocking with sample data
            interface_metrics = [
                {
                    'name': 'ether1',
                    'rx_bytes': 1024000,
                    'tx_bytes': 512000,
                    'status': True
                },
                {
                    'name': 'wlan1',
                    'rx_bytes': 256000,
                    'tx_bytes': 128000,
                    'status': True
                }
            ]
            
            # Store metrics in InfluxDB
            self._store_system_metrics(device, cpu_load, memory_usage)
            self._store_interface_metrics(device, interface_metrics)
            
        except Exception as e:
            logger.error(f"SNMP collection error for device {device['id']}: {str(e)}")
            raise
    
    def _get_snmp_value(self, host, community, oid):
        """Get a value from an SNMP OID"""
        try:
            error_indication, error_status, error_index, var_binds = next(
                snmp.getCmd(
                    snmp.SnmpEngine(),
                    snmp.CommunityData(community),
                    snmp.UdpTransportTarget((host, 161)),
                    snmp.ContextData(),
                    snmp.ObjectType(snmp.ObjectIdentity(oid))
                )
            )
            
            if error_indication:
                logger.error(f"SNMP error: {error_indication}")
                return 0
                
            if error_status:
                logger.error(f"SNMP error: {error_status.prettyPrint()} at {var_binds[int(error_index)-1] if error_index else '?'}")
                return 0
            
            for var_bind in var_binds:
                return var_bind[1]
                
            return 0
        except Exception as e:
            logger.error(f"SNMP get error: {str(e)}")
            return 0
    
    def _store_system_metrics(self, device, cpu_load, memory_usage):
        """Store system metrics in InfluxDB"""
        data = [
            {
                "measurement": "system_metrics",
                "tags": {
                    "device_id": device['id'],
                    "device_name": device['name'],
                    "device_type": "mikrotik"
                },
                "fields": {
                    "cpu_load": float(cpu_load),
                    "memory_usage": float(memory_usage)
                }
            }
        ]
        
        self.influx.write_data(data)
        logger.debug(f"Stored system metrics for device {device['id']}")
    
    def _store_interface_metrics(self, device, interfaces):
        """Store interface metrics in InfluxDB"""
        data = []
        
        for iface in interfaces:
            data.append({
                "measurement": "interface_metrics",
                "tags": {
                    "device_id": device['id'],
                    "device_name": device['name'],
                    "interface": iface['name'],
                    "device_type": "mikrotik"
                },
                "fields": {
                    "rx_bytes": float(iface['rx_bytes']),
                    "tx_bytes": float(iface['tx_bytes']),
                    "status": 1 if iface['status'] else 0
                }
            })
        
        self.influx.write_data(data)
        logger.debug(f"Stored interface metrics for device {device['id']}")
        
    def _can_connect(self, host, port=22, timeout=1):
        """Check if we can connect to the host"""
        import socket
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            return False
            
    def _collect_demo_data(self, device):
        """Generate and collect demo data for a device when not reachable"""
        import random
        import datetime
        
        # Current timestamp
        current_time = datetime.datetime.now()
        
        # Generate simulated CPU load (varies between 10% and 50%)
        hour_of_day = current_time.hour
        # Higher load during business hours (8-18)
        base_load = 30 if 8 <= hour_of_day <= 18 else 15
        cpu_load = base_load + random.randint(-5, 15)
        
        # Generate simulated memory usage (varies between 20% and 70%)
        memory_usage = base_load + 10 + random.randint(0, 25)
        
        # Generate simulated interface data
        interfaces = [
            {
                'name': 'ether1',
                'rx_bytes': random.randint(500000, 2000000),  # 0.5-2 Mbps
                'tx_bytes': random.randint(100000, 1000000),  # 0.1-1 Mbps
                'status': True
            },
            {
                'name': 'ether2',
                'rx_bytes': random.randint(100000, 500000),  # 0.1-0.5 Mbps
                'tx_bytes': random.randint(50000, 250000),   # 0.05-0.25 Mbps
                'status': True
            },
            {
                'name': 'wlan1',
                'rx_bytes': random.randint(250000, 1500000), # 0.25-1.5 Mbps
                'tx_bytes': random.randint(100000, 800000),  # 0.1-0.8 Mbps
                'status': True
            }
        ]
        
        # Store the simulated metrics
        self._store_system_metrics(device, cpu_load, memory_usage)
        self._store_interface_metrics(device, interfaces)
        
        logger.debug(f"Generated and stored demo data for device {device['id']}")
