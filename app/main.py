#!/usr/bin/env python3
"""
MikroTik Network Monitoring System
Main application entry point
"""
import logging
import os
import sys
import time
import threading
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('netmon')

def load_config():
    """Load the application configuration from config.yaml"""
    config_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),  # From app directory
        os.path.join(os.path.dirname(__file__), 'config.yaml'),        # From app directory (direct)
        os.path.join(os.getcwd(), 'config.yaml'),                      # From current working directory
        '/app/config.yaml',                                            # For Docker compatibility
    ]
    
    for config_path in config_paths:
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            logger.debug(f"Could not load config from {config_path}: {str(e)}")
    
    logger.error(f"Failed to load configuration: No configuration file found")
    return None

def initialize_collectors(config):
    """Initialize data collectors based on configuration"""
    collectors = []
    
    # Load enabled modules
    enabled_modules = config.get('modules', [])
    
    if 'system' in enabled_modules:
        try:
            from collectors.system import Collector as SystemCollector
            collectors.append(SystemCollector(config))
            logger.info("Initialized System collector")
        except Exception as e:
            logger.error(f"Failed to initialize System collector: {str(e)}")
    
    if 'mikrotik' in enabled_modules:
        try:
            from collectors.mikrotik import Collector as MikrotikCollector
            collectors.append(MikrotikCollector(config))
            logger.info("Initialized MikroTik collector")
        except Exception as e:
            logger.error(f"Failed to initialize MikroTik collector: {str(e)}")
    
    if 'wireless' in enabled_modules:
        try:
            from collectors.wireless import Collector as WirelessCollector
            collectors.append(WirelessCollector(config))
            logger.info("Initialized Wireless collector")
        except Exception as e:
            logger.error(f"Failed to initialize Wireless collector: {str(e)}")
    
    if 'wan' in enabled_modules:
        try:
            from collectors.wan import Collector as WanCollector
            collectors.append(WanCollector(config))
            logger.info("Initialized WAN collector")
        except Exception as e:
            logger.error(f"Failed to initialize WAN collector: {str(e)}")
    
    if 'qos' in enabled_modules:
        try:
            from collectors.qos import Collector as QosCollector
            collectors.append(QosCollector(config))
            logger.info("Initialized QoS collector")
        except Exception as e:
            logger.error(f"Failed to initialize QoS collector: {str(e)}")
    
    # Initialize all collectors
    for collector in collectors:
        try:
            collector.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize collector {collector.__class__.__name__}: {str(e)}")
    
    return collectors

def run_collector(collector):
    """Run a collector in a loop"""
    while True:
        try:
            collector.collect()
            # Wait for the next interval
            time.sleep(60)  # Default 1-minute interval
        except Exception as e:
            logger.error(f"Error in collector {collector.__class__.__name__}: {str(e)}")
            time.sleep(10)  # Wait a bit before retrying

def start_collectors(collectors):
    """Start all collectors in separate threads"""
    threads = []
    
    for collector in collectors:
        thread = threading.Thread(
            target=run_collector,
            args=(collector,),
            name=f"collector-{collector.__class__.__name__}"
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
        logger.info(f"Started collector: {collector.__class__.__name__}")
    
    return threads

def main():
    """Main application entry point"""
    logger.info("Starting MikroTik Network Monitoring System")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration, exiting.")
        return 1
    
    try:
        # Initialize collectors
        collectors = initialize_collectors(config)
        
        # Start collectors
        collector_threads = start_collectors(collectors)
        
        # Keep the main thread alive
        while True:
            # Check if all collector threads are alive
            for thread in collector_threads:
                if not thread.is_alive():
                    logger.warning(f"Collector thread {thread.name} died, restarting...")
                    # TODO: Implement proper restart mechanism
            
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())