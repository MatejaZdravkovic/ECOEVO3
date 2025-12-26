#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# EcoEvoCRM GUI Application
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Entry point for the real-time simulation interface
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import sys
from PyQt5.QtWidgets import QApplication
from ecoevocrm.gui.main_window import MainWindow

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def main():
    """
    Launch the EcoEvoCRM GUI application.

    Creates the Qt application instance, initializes the main window,
    and starts the event loop.
    """
    #------------------------------
    # Create Qt application
    #------------------------------
    app = QApplication(sys.argv)

    #------------------------------
    # Set application metadata
    #------------------------------
    app.setApplicationName("EcoEvoCRM Simulator")
    app.setOrganizationName("EcoEvoCRM")
    app.setApplicationDisplayName("EcoEvoCRM Real-time Simulator")

    #------------------------------
    # Create and show main window
    #------------------------------
    window = MainWindow()
    window.show()

    #------------------------------
    # Start event loop
    #------------------------------
    sys.exit(app.exec_())

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == '__main__':
    main()

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
