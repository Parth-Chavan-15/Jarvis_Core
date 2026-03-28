# agent/tools.py
import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def execute_create_folder(folder_name: str, target_directory: str = "desktop") -> str:
    """Physically creates a folder on the Windows machine."""
    try:
        # Route the directory based on user input
        if "document" in target_directory.lower():
            base_path = os.path.join(os.environ['USERPROFILE'], 'Documents')
        elif "download" in target_directory.lower():
            base_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')
        else:
            base_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
            
        full_path = os.path.join(base_path, folder_name)
        
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            return f"Success. I have created the folder '{folder_name}' in your {target_directory}."
        else:
            return f"Sir, a folder named '{folder_name}' already exists in that location."
            
    except Exception as e:
        logger.error(f"Folder creation failed: {e}")
        return "I encountered a system permissions error while trying to create the directory."

def execute_open_app(app_name: str) -> str:
    """Physically opens standard Windows applications."""
    # THE FIX: Strip out spaces and punctuation so "note pad." becomes "notepad"
    clean_name = app_name.lower().replace(" ", "").replace(".", "").strip()
    
    try:
        if "notepad" in clean_name:
            subprocess.Popen(["notepad.exe"])
            return "Notepad launched successfully."
            
        elif "calculator" in clean_name or "calc" in clean_name:
            subprocess.Popen(["calc.exe"])
            return "Calculator is now open."
            
        elif "chrome" in clean_name:
            # THE FIX: Added Chrome! Uses the Windows 'start' command
            os.system("start chrome")
            return "Google Chrome launched successfully."
            
        elif "edge" in clean_name or "browser" in clean_name:
            os.system("start msedge")
            return "Microsoft Edge launched."
            
        else:
            return f"I cannot find the executable path for {app_name} yet. You need to add it to my tools."
            
    except Exception as e:
        logger.error(f"Failed to open app: {e}")
        return f"I was unable to open {app_name}."
    """Physically opens standard Windows applications."""
    app_name = app_name.lower()
    try:
        if "notepad" in app_name:
            subprocess.Popen(["notepad.exe"])
            return "Notepad launched successfully."
        elif "calculator" in app_name or "calc" in app_name:
            subprocess.Popen(["calc.exe"])
            return "Calculator is now open."
        else:
            return f"I cannot find the executable path for {app_name} yet."
    except Exception as e:
        logger.error(f"Failed to open app: {e}")
        return f"I was unable to open {app_name}."

def get_time() -> str:
    now = datetime.now().strftime("%I:%M %p")
    return f"The current system time is {now}."