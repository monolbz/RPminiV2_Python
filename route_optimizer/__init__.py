"""
Madrid Route Optimizer Package

A modular route optimization tool using Google Maps API.

Modules:
    - cache: Cache management for API responses
    - api: Google Maps API integration
    - utils: Utility functions (calculations, formatting, URL generation)
    - input_handler: Input file reading and validation
    - main: Main application logic and display
"""

__version__ = "2.0.0"
__author__ = "monolbz"

# Export main function for easy access
from .main import main

__all__ = ['main']
