"""
Network monitoring collectors package
Contains data collectors for various device types and metrics
"""

class BaseCollector:
    """Base class for all data collectors"""
    
    def __init__(self, config):
        """Initialize the collector with configuration"""
        self.config = config
        self.interval = 60  # Default collection interval in seconds
        self.initialize()
        
    def initialize(self):
        """Initialize collector-specific resources"""
        pass
        
    def collect(self):
        """Collect metrics - to be implemented by subclasses"""
        raise NotImplementedError("Collector subclasses must implement collect()")
