#!/usr/bin/env python
"""
Create a desktop shortcut for EcoEvoCRM Simulator

This script creates a Windows desktop shortcut (.lnk) that launches the GUI.
Run this script once to install the shortcut on your desktop.
"""

import os
import sys

try:
    import winshell
    from win32com.client import Dispatch
except ImportError:
    print("ERROR: Required packages not installed")
    print("Please install with: pip install pywin32 winshell")
    sys.exit(1)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def create_shortcut():
    """Create desktop shortcut for EcoEvoCRM Simulator."""

    #------------------------------
    # Get desktop path
    #------------------------------
    desktop = winshell.desktop()

    #------------------------------
    # Define shortcut properties
    #------------------------------
    shortcut_path = os.path.join(desktop, "EcoEvoCRM Simulator.lnk")
    target_executable = sys.executable  # Python interpreter path
    working_directory = os.path.dirname(os.path.abspath(__file__))
    launch_script = os.path.join(working_directory, "launch_gui.py")
    icon_location = target_executable  # Use Python icon

    #------------------------------
    # Create shortcut
    #------------------------------
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_executable.replace("python.exe", "pythonw.exe")
    shortcut.Arguments = f'"{launch_script}"'
    shortcut.WorkingDirectory = working_directory
    shortcut.IconLocation = icon_location
    shortcut.Description = "EcoEvoCRM Real-time Evolutionary Simulator"
    shortcut.save()

    print("="*60)
    print("Desktop shortcut created successfully!")
    print("="*60)
    print(f"Location: {shortcut_path}")
    print(f"Target: {target_executable}")
    print(f"Working directory: {working_directory}")
    print("\nYou can now double-click the shortcut on your desktop")
    print("to launch EcoEvoCRM Simulator!")
    print("="*60)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

if __name__ == "__main__":
    try:
        create_shortcut()
    except Exception as e:
        print(f"ERROR: Failed to create shortcut: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
