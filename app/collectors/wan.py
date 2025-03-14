"""
WAN collector module
Collects metrics from internet connection (WAN) interfaces
"""
import time
import logging
import subprocess
from . import BaseCollector
from utils.influx import InfluxClient

# Configure logging
logger = logging.getLogger("collectors.wan")

class Collector(BaseCollector):
    """Collector for WAN metrics"""
    
    def __init__(self, config):
        """Initialize WAN collector"""
        self.interval = 120  # Collect every 2 minutes
        self.devices = []  # Will be populated in initialize()
        self.influx = None
        self.target_hosts = ['8.8.8.8', '1.1.1.1']  # Default ping targets
        super().__init__(config)
    
    def initialize(self):
        """Initialize collector resources"""
        # Create InfluxDB client
        influx_config = self.config.get('influxdb', {})
        self.influx = InfluxClient(
            host=influx_config.get('host', 'localhost'),
            port=influx_config.get('port', 8086),
            token=influx_config.get('token', 'nmlyZh-d8XfFkR-3oknXFJx_oDhtu9RCsn_qaK6LYLkFuwgX5xzKmTo-h4K3dtRcKJPxdr1YI8vyf00B0tH2tA=='),
            org=influx_config.get('org', 'my-org'),
            bucket=influx_config.get('bucket', 'my-bucket')
        )
        
        # Load device and interface information
        # In a real application, this would come from a database
        # For demo purposes, we'll hardcode some test data
        self.devices = [
            {
                'id': 'mikrotik1',
                'name': 'Main Router',
                'interfaces': [
                    {
                        'name': 'ether1',
                        'type': 'wan',
                        'description': 'ISP1 Connection'
                    },
                    {
                        'name': 'ether2',
                        'type': 'wan',
                        'description': 'ISP2 Backup'
                    }
                ]
            }
        ]
        
        logger.info(f"Initialized WAN collector with {len(self.devices)} devices")
    
    def collect(self):
        """Collect WAN metrics"""
        start_time = time.time()
        logger.debug("Starting WAN metrics collection")
        
        # Measure internet connectivity
        ping_results = self._measure_connectivity()
        
        # Store ping metrics in InfluxDB
        self._store_ping_metrics(ping_results)
        
        # In a real implementation, we would also collect additional WAN metrics
        # from the actual devices, like bandwidth usage, connection state, etc.
        
        elapsed = time.time() - start_time
        logger.debug(f"Completed WAN metrics collection in {elapsed:.2f} seconds")
    
    def _measure_connectivity(self):
        """Measure internet connectivity using ping"""
        results = []
        
        for target in self.target_hosts:
            try:
                # Use specific inetutils-ping path we found with `which ping`
                cmd_options = [
                    ['/nix/store/p83llzv0lwnnblzc7h12dqdr7fmrmlcx-inetutils-2.5/bin/ping', '-c', '5', '-q', target],
                    ['ping', '-c', '5', '-q', target]
                ]
                
                for cmd in cmd_options:
                    try:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        stdout, stderr = process.communicate()
                        if process.returncode == 0 or process.returncode == 1:
                            # Parse ping output
                            output = stdout.decode('utf-8')
                            break
                    except:
                        continue
                else:
                    # All ping commands failed
                    raise Exception("No working ping command found")
                
                # Check if ping was successful
                if process.returncode == 0:
                    # Extract packet loss
                    packet_loss = 100.0
                    for line in output.split('\n'):
                        if 'packet loss' in line:
                            try:
                                packet_loss = float(line.split('%')[0].split(' ')[-1])
                            except:
                                packet_loss = 100.0
                    
                    # Extract round-trip times
                    rtt_min = rtt_avg = rtt_max = rtt_mdev = 0.0
                    for line in output.split('\n'):
                        if 'rtt min/avg/max/mdev' in line:
                            try:
                                rtt_parts = line.split(' = ')[1].split('/')
                                rtt_min = float(rtt_parts[0])
                                rtt_avg = float(rtt_parts[1])
                                rtt_max = float(rtt_parts[2])
                                rtt_mdev = float(rtt_parts[3].split(' ')[0])
                            except:
                                pass
                    
                    results.append({
                        'target': target,
                        'success': True,
                        'packet_loss': packet_loss,
                        'rtt_min': rtt_min,
                        'rtt_avg': rtt_avg,
                        'rtt_max': rtt_max,
                        'rtt_mdev': rtt_mdev
                    })
                else:
                    # Ping failed
                    results.append({
                        'target': target,
                        'success': False,
                        'packet_loss': 100.0,
                        'rtt_min': 0.0,
                        'rtt_avg': 0.0,
                        'rtt_max': 0.0,
                        'rtt_mdev': 0.0
                    })
            except Exception as e:
                logger.error(f"Error pinging {target}: {str(e)}")
                results.append({
                    'target': target,
                    'success': False,
                    'packet_loss': 100.0,
                    'rtt_min': 0.0,
                    'rtt_avg': 0.0,
                    'rtt_max': 0.0,
                    'rtt_mdev': 0.0
                })
        
        return results
    
    def _store_ping_metrics(self, ping_results):
        """Store ping metrics in InfluxDB"""
        data = []
        
        for result in ping_results:
            data.append({
                "measurement": "wan_connectivity",
                "tags": {
                    "target": result['target'],
                    "type": "ping"
                },
                "fields": {
                    "success": 1 if result['success'] else 0,
                    "packet_loss": float(result['packet_loss']),
                    "rtt_min": float(result['rtt_min']),
                    "rtt_avg": float(result['rtt_avg']),
                    "rtt_max": float(result['rtt_max']),
                    "rtt_mdev": float(result['rtt_mdev'])
                }
            })
        
        self.influx.write_data(data)
        logger.debug(f"Stored WAN connectivity metrics for {len(ping_results)} targets")
    
    def _collect_interface_metrics(self):
        """
        Collect interface metrics for WAN interfaces
        
        Note: In a real implementation, this would connect to the network devices
        and collect actual interface metrics. For this example, we're keeping it
        simple with just the ping metrics above.
        """
        pass
