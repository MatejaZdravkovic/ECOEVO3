#!/usr/bin/env python
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Suppression Model Real-time Simulator - Entry Point
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch script for the suppression model desktop GUI application
#
# Usage:
#   python run_suppression_app.py
#
# Or from VS Code: Right-click and select "Run Python File in Terminal"
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
import multiprocessing as mp
from PyQt5.QtWidgets import QApplication

# Add src directory to path so imports work
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ecoevocrm.gui.suppression_window import SuppressionWindow

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    """
    Main entry point for the suppression model application.

    Creates Qt application and shows the main window.
    """
    # Required for multiprocessing on Windows/Mac
    mp.set_start_method('spawn', force=True)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("EcoEvoCRM - Suppression Model Simulator")

    # Create and show main window
    window = SuppressionWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec_())

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
