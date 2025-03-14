"""
Wireless collector module
Collects wireless metrics from MikroTik and other wireless devices
"""
import time
import logging
from . import BaseCollector
from utils.influx import InfluxClient

# Try to import SNMP libraries
try:
    import pysnmp.hlapi as snmp
    HAVE_SNMP = True
except ImportError:
    HAVE_SNMP = False
    logging.warning("pysnmp not available, wireless monitoring may be limited")

# Optional: Use librouteros if available
try:
    import librouteros
    HAVE_ROUTEROS = True
except ImportError:
    HAVE_ROUTEROS = False
    logging.warning("librouteros not available, using SNMP for MikroTik wireless")

# Configure logging
logger = logging.getLogger("collectors.wireless")

class Collector(BaseCollector):
    """Collector for wireless metrics"""
    
    def __init__(self, config):
        """Initialize wireless collector"""
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
        
        logger.info(f"Initialized wireless collector with {len(self.devices)} devices")
    
    def collect(self):
        """Collect wireless metrics from all devices"""
        start_time = time.time()
        logger.debug("Starting wireless metrics collection")
        
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
                logger.error(f"Error collecting wireless metrics for device {device['id']}: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.debug(f"Completed wireless metrics collection in {elapsed:.2f} seconds")
    
    def _collect_mikrotik_api(self, device):
        """Collect wireless metrics using MikroTik API"""
        try:
            # Connect to RouterOS API
            api = librouteros.connect(
                host=device['host'],
                username=device['api_user'],
                password=device['api_password']
            )
            
            # Collect wireless interfaces
            wireless_interfaces = api.path('/interface/wireless').get()
            
            # Collect wireless registration table (connected clients)
            wireless_registrations = api.path('/interface/wireless/registration-table').get()
            
            # Process wireless interfaces
            interface_metrics = []
            for iface in wireless_interfaces:
                interface_metrics.append({
                    'name': iface.get('name', 'unknown'),
                    'mac_address': iface.get('mac-address', ''),
                    'ssid': iface.get('ssid', ''),
                    'frequency': int(iface.get('frequency', 0)),
                    'band': iface.get('band', ''),
                    'channel_width': iface.get('channel-width', ''),
                    'mode': iface.get('mode', ''),
                    'tx_power': int(iface.get('tx-power', 0)),
                    'status': iface.get('running', False)
                })
            
            # Process wireless clients
            client_metrics = []
            for client in wireless_registrations:
                client_metrics.append({
                    'mac_address': client.get('mac-address', ''),
                    'interface': client.get('interface', ''),
                    'signal_strength': int(client.get('signal-strength', 0)),
                    'signal_to_noise': int(client.get('signal-to-noise', 0)),
                    'tx_rate': int(client.get('tx-rate', 0)),
                    'rx_rate': int(client.get('rx-rate', 0)),
                    'uptime': client.get('uptime', '')
                })
            
            # Store metrics in InfluxDB
            self._store_interface_metrics(device, interface_metrics)
            self._store_client_metrics(device, client_metrics)
            
        except Exception as e:
            logger.error(f"API collection error for device {device['id']}: {str(e)}")
            raise
    
    def _collect_mikrotik_snmp(self, device):
        """Collect wireless metrics using SNMP"""
        try:
            # SNMP connection parameters
            host = device['host']
            community = device.get('snmp_community', 'public')
            
            # In a real implementation, we would perform SNMP walks to collect
            # wireless interface data and client information
            
            # For demonstration purposes, mocking with sample data
            interface_metrics = [
                {
                    'name': 'wlan1',
                    'mac_address': '00:11:22:33:44:55',
                    'ssid': 'MyNetwork',
                    'frequency': 2412,
                    'band': '2ghz-b/g/n',
                    'channel_width': '20MHz',
                    'mode': 'ap-bridge',
                    'tx_power': 20,
                    'status': True
                }
            ]
            
            client_metrics = [
                {
                    'mac_address': 'AA:BB:CC:DD:EE:FF',
                    'interface': 'wlan1',
                    'signal_strength': -65,
                    'signal_to_noise': 25,
                    'tx_rate': 65000,
                    'rx_rate': 54000,
                    'uptime': '1h23m45s'
                }
            ]
            
            # Store metrics in InfluxDB
            self._store_interface_metrics(device, interface_metrics)
            self._store_client_metrics(device, client_metrics)
            
        except Exception as e:
            logger.error(f"SNMP collection error for device {device['id']}: {str(e)}")
            raise
    
    def _store_interface_metrics(self, device, interfaces):
        """Store wireless interface metrics in InfluxDB"""
        data = []
        
        for iface in interfaces:
            data.append({
                "measurement": "wireless_interface",
                "tags": {
                    "device_id": device['id'],
                    "device_name": device['name'],
                    "interface": iface['name'],
                    "mac_address": iface['mac_address'],
                    "ssid": iface['ssid'],
                    "band": iface['band'],
                    "mode": iface['mode']
                },
                "fields": {
                    "frequency": float(iface['frequency']),
                    "tx_power": float(iface['tx_power']),
                    "status": 1 if iface['status'] else 0
                }
            })
        
        self.influx.write_data(data)
        logger.debug(f"Stored wireless interface metrics for device {device['id']}")
    
    def _store_client_metrics(self, device, clients):
        """Store wireless client metrics in InfluxDB"""
        data = []
        
        for client in clients:
            # Convert string uptime to seconds if possible
            uptime_sec = 0
            uptime = client.get('uptime', '')
            if isinstance(uptime, str):
                try:
                    # Parse uptime string like "1h23m45s"
                    hours = minutes = seconds = 0
                    if 'h' in uptime:
                        hours, uptime = uptime.split('h', 1)
                        hours = int(hours)
                    if 'm' in uptime:
                        minutes, uptime = uptime.split('m', 1)
                        minutes = int(minutes)
                    if 's' in uptime:
                        seconds = int(uptime.replace('s', ''))
                    uptime_sec = hours * 3600 + minutes * 60 + seconds
                except:
                    uptime_sec = 0
            
            data.append({
                "measurement": "wireless_client",
                "tags": {
                    "device_id": device['id'],
                    "device_name": device['name'],
                    "interface": client['interface'],
                    "mac_address": client['mac_address']
                },
                "fields": {
                    "signal_strength": float(client['signal_strength']),
                    "signal_to_noise": float(client['signal_to_noise']),
                    "tx_rate": float(client['tx_rate']),
                    "rx_rate": float(client['rx_rate']),
                    "uptime_seconds": float(uptime_sec)
                }
            })
        
        self.influx.write_data(data)
        logger.debug(f"Stored wireless client metrics for device {device['id']}")
