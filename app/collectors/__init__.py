"""
Network monitoring collectors package
Contains data collectors for various device types and metrics
"""

import logging
from abc import ABC, abstractmethod

class BaseCollector:
    """Base class for all data collectors"""
    
    def __init__(self, config):
        """Initialize the collector with configuration"""
        self.config = config
        self.logger = logging.getLogger(f'collectors.{self.__class__.__module__.split(".")[-1]}')
        
    def initialize(self):
        """Initialize collector-specific resources"""
        pass  # Default implementation does nothing
    
    @abstractmethod
    def collect(self):
        """Collect metrics - to be implemented by subclasses"""
        pass