#!/usr/bin/env python
"""
Quick launcher for EcoEvoCRM GUI
Run this script to start the application
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the application
from ecoevocrm.app import main

if __name__ == '__main__':
    print("="*60)
    print("  EcoEvoCRM Real-time Simulator")
    print("="*60)
    print("\nLaunching GUI application...")
    print("\nQuick Test Settings (for fast results):")
    print("  - T: 1000")
    print("  - dt: 10")
    print("  - Keep other defaults")
    print("  - Click 'Run Simulation'")
    print("\n" + "="*60 + "\n")

    main()
