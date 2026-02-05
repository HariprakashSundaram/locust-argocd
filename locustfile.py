"""
Main Locustfile - Multi-site Load Testing
Dynamically imports test classes from scripts
"""

from google_load_test import GoogleLoadTest
from demoblaze_load_test import DemoBlazeLoadTest
from opencart_load_test import OpenCartLoadTest

__all__ = [
    'GoogleLoadTest',
    'DemoBlazeLoadTest', 
    'OpenCartLoadTest'
]
