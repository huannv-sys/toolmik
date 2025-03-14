"""
System collector module
Collects system metrics (CPU, memory, disk) from the local system
"""
import os
import time
import psutil
import logging
import platform
from . import BaseCollector
from utils.influx import InfluxClient

# Configure logging
logger = logging.getLogger("collectors.system")

class Collector(BaseCollector):
    """Collector for local system metrics"""
    
    def __init__(self, config):
        """Initialize system collector"""
        self.interval = 60  # Collect every 60 seconds
        self.influx = None
        self.system_info = {}
        super().__init__(config)
    
    def initialize(self):
        """Initialize collector resources"""
        # Create InfluxDB client
        influx_config = self.config.get('influxdb', {})
        self.influx = InfluxClient(
            host=influx_config.get('host', 'influxdb'),
            port=influx_config.get('port', 8086),
            token=influx_config.get('token', 'ChangeThisPassword'),
            org=influx_config.get('org', 'my-org'),
            bucket=influx_config.get('bucket', 'my-bucket')
        )
        
        # Collect static system information
        self.system_info = {
            'hostname': platform.node(),
            'os': platform.system(),
            'os_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'cpu_cores': psutil.cpu_count(logical=True),
            'physical_cpu_cores': psutil.cpu_count(logical=False)
        }
        
        logger.info("Initialized system collector")
    
    def collect(self):
        """Collect system metrics"""
        start_time = time.time()
        logger.debug("Starting system metrics collection")
        
        try:
            # Collect CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_times = psutil.cpu_times_percent(interval=1)
            
            # Collect memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Collect disk metrics
            disk_partitions = psutil.disk_partitions()
            disk_metrics = []
            
            for partition in disk_partitions:
                if partition.fstype:  # Skip empty partitions
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_metrics.append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        })
                    except PermissionError:
                        # Some mountpoints might not be accessible
                        pass
            
            # Collect network metrics
            net_io_counters = psutil.net_io_counters(pernic=True)
            network_metrics = []
            
            for interface, counters in net_io_counters.items():
                network_metrics.append({
                    'interface': interface,
                    'bytes_sent': counters.bytes_sent,
                    'bytes_recv': counters.bytes_recv,
                    'packets_sent': counters.packets_sent,
                    'packets_recv': counters.packets_recv,
                    'errin': counters.errin,
                    'errout': counters.errout,
                    'dropin': counters.dropin,
                    'dropout': counters.dropout
                })
            
            # Store metrics in InfluxDB
            self._store_cpu_metrics(cpu_percent, cpu_times)
            self._store_memory_metrics(memory, swap)
            self._store_disk_metrics(disk_metrics)
            self._store_network_metrics(network_metrics)
            
            # Check thresholds and trigger alerts if needed
            self._check_thresholds(cpu_percent, memory.percent, disk_metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.debug(f"Completed system metrics collection in {elapsed:.2f} seconds")
    
    def _store_cpu_metrics(self, cpu_percent, cpu_times):
        """Store CPU metrics in InfluxDB"""
        data = [
            {
                "measurement": "cpu_metrics",
                "tags": {
                    "hostname": self.system_info['hostname'],
                    "os": self.system_info['os'],
                    "type": "system"
                },
                "fields": {
                    "cpu_percent": float(cpu_percent),
                    "user_percent": float(cpu_times.user),
                    "system_percent": float(cpu_times.system),
                    "idle_percent": float(cpu_times.idle)
                }
            }
        ]
        
        self.influx.write_data(data)
        logger.debug("Stored CPU metrics")
    
    def _store_memory_metrics(self, memory, swap):
        """Store memory metrics in InfluxDB"""
        data = [
            {
                "measurement": "memory_metrics",
                "tags": {
                    "hostname": self.system_info['hostname'],
                    "os": self.system_info['os'],
                    "type": "system"
                },
                "fields": {
                    "total": float(memory.total),
                    "available": float(memory.available),
                    "used": float(memory.used),
                    "free": float(memory.free),
                    "percent": float(memory.percent),
                    "swap_total": float(swap.total),
                    "swap_used": float(swap.used),
                    "swap_free": float(swap.free),
                    "swap_percent": float(swap.percent)
                }
            }
        ]
        
        self.influx.write_data(data)
        logger.debug("Stored memory metrics")
    
    def _store_disk_metrics(self, disk_metrics):
        """Store disk metrics in InfluxDB"""
        data = []
        
        for disk in disk_metrics:
            data.append({
                "measurement": "disk_metrics",
                "tags": {
                    "hostname": self.system_info['hostname'],
                    "os": self.system_info['os'],
                    "device": disk['device'],
                    "mountpoint": disk['mountpoint'],
                    "fstype": disk['fstype'],
                    "type": "system"
                },
                "fields": {
                    "total": float(disk['total']),
                    "used": float(disk['used']),
                    "free": float(disk['free']),
                    "percent": float(disk['percent'])
                }
            })
        
        self.influx.write_data(data)
        logger.debug("Stored disk metrics")
    
    def _store_network_metrics(self, network_metrics):
        """Store network metrics in InfluxDB"""
        data = []
        
        for net in network_metrics:
            data.append({
                "measurement": "network_metrics",
                "tags": {
                    "hostname": self.system_info['hostname'],
                    "os": self.system_info['os'],
                    "interface": net['interface'],
                    "type": "system"
                },
                "fields": {
                    "bytes_sent": float(net['bytes_sent']),
                    "bytes_recv": float(net['bytes_recv']),
                    "packets_sent": float(net['packets_sent']),
                    "packets_recv": float(net['packets_recv']),
                    "errin": float(net['errin']),
                    "errout": float(net['errout']),
                    "dropin": float(net['dropin']),
                    "dropout": float(net['dropout'])
                }
            })
        
        self.influx.write_data(data)
        logger.debug("Stored network metrics")
    
    def _check_thresholds(self, cpu_percent, memory_percent, disk_metrics):
        """Check if any metrics exceed defined thresholds"""
        from utils.alerting import send_alert
        
        thresholds = self.config.get('alerting', {}).get('threshold', {})
        cpu_threshold = thresholds.get('cpu', 80)
        memory_threshold = thresholds.get('memory', 85)
        disk_threshold = thresholds.get('disk', 90)
        
        # Check CPU threshold
        if cpu_percent > cpu_threshold:
            message = f"CPU usage alert: {cpu_percent}% (threshold: {cpu_threshold}%)"
            send_alert('cpu', message, self.system_info['hostname'], cpu_percent, cpu_threshold)
        
        # Check memory threshold
        if memory_percent > memory_threshold:
            message = f"Memory usage alert: {memory_percent}% (threshold: {memory_threshold}%)"
            send_alert('memory', message, self.system_info['hostname'], memory_percent, memory_threshold)
        
        # Check disk thresholds
        for disk in disk_metrics:
            if disk['percent'] > disk_threshold:
                message = f"Disk usage alert: {disk['mountpoint']} at {disk['percent']}% (threshold: {disk_threshold}%)"
                send_alert('disk', message, self.system_info['hostname'], disk['percent'], disk_threshold, disk['mountpoint'])
