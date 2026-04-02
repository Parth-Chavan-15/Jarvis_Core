# agent/tools.py
import os
import subprocess
import logging
import shutil
import threading
import time as pytime
from datetime import datetime

logger = logging.getLogger(__name__)

def _get_base_path(target_directory: str) -> str:
    """Helper function to find the right Windows directory."""
    target_directory = target_directory.lower()
    if "document" in target_directory:
        return os.path.join(os.environ['USERPROFILE'], 'Documents')
    elif "download" in target_directory:
        return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:
        # Defaults to Desktop
        return os.path.join(os.environ['USERPROFILE'], 'Desktop')

def execute_create_folder(folder_name: str, target_directory: str = "desktop") -> str:
    """Physically creates a folder."""
    try:
        base_path = _get_base_path(target_directory)
        full_path = os.path.join(base_path, folder_name)
        
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            return f"Success. I have created '{folder_name}' in your {target_directory}."
        else:
            return f"Sir, '{folder_name}' already exists in that location."
            
    except Exception as e:
        logger.error(f"Folder creation failed: {e}")
        return "I encountered a system permissions error."

def execute_delete_item(item_name: str, target_directory: str = "desktop") -> str:
    """Deletes a file or folder (Requires Confirmation)."""
    try:
        base_path = _get_base_path(target_directory)
        full_path = os.path.join(base_path, item_name)

        if not os.path.exists(full_path):
            return f"Sir, I could not find '{item_name}' in your {target_directory}."

        if os.path.isdir(full_path):
            shutil.rmtree(full_path) # Deletes folder and everything inside it
            return f"I have successfully deleted the folder '{item_name}'."
        else:
            os.remove(full_path) # Deletes a single file
            return f"I have successfully deleted the file '{item_name}'."
            
    except Exception as e:
        logger.error(f"Deletion failed: {e}")
        return "I encountered an error. The file might be open in another program."

def execute_rename_item(old_name: str, new_name: str, target_directory: str = "desktop") -> str:
    """Renames a file or folder."""
    try:
        base_path = _get_base_path(target_directory)
        old_path = os.path.join(base_path, old_name)
        new_path = os.path.join(base_path, new_name)

        if not os.path.exists(old_path):
            return f"Sir, I could not find '{old_name}' to rename."

        os.rename(old_path, new_path)
        return f"Successfully renamed '{old_name}' to '{new_name}'."
            
    except Exception as e:
        logger.error(f"Rename failed: {e}")
        return "I encountered an error trying to rename the item."

def execute_open_app(app_name: str) -> str:
    """Universal App Launcher using Windows shortcuts."""
    clean_name = app_name.lower().replace(" ", "").replace(".", "").strip()
    
    # Map common English words to their weird Windows executable names
    app_aliases = {
        "word": "winword",
        "powerpoint": "powerpnt",
        "excel": "excel",
        "vscode": "code",
        "visualstudiocode": "code",
        "commandprompt": "cmd",
        "browser": "msedge"
    }
    
    exe_name = app_aliases.get(clean_name, clean_name)
    
    try:
        # THE FIX: Use subprocess to check if Windows actually succeeded
        # shell=True is required for the 'start' command
        result = subprocess.run(f"start {exe_name}", shell=True)
        
        # returncode 0 means success. Anything else means Windows threw an error.
        if result.returncode == 0:
            return f"I have launched {app_name}."
        else:
            return f"Sir, I could not find an application named '{app_name}' installed on your system."
            
    except Exception as e:
        logger.error(f"Failed to open app: {e}")
        return f"I was unable to open {app_name}."

def get_time() -> str:
    now = datetime.now().strftime("%I:%M %p")
    return f"The current system time is {now}."

def get_date() -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."

def start_timer(amount: int, unit: str) -> str:
    """Runs a timer in the background without freezing Jarvis."""
    multiplier = 1 if "second" in unit else 60 if "minute" in unit else 3600
    
    def background_timer():
        pytime.sleep(amount * multiplier)
        from agent.voice import speak_text
        import agent.state as state
        # Wait until Jarvis is free to speak the alarm
        while state.current_state == "speaking":
            pytime.sleep(1)
        
        old_state = state.current_state
        state.current_state = "speaking"
        speak_text(f"Sir, your {amount} {unit} timer has concluded.")
        state.current_state = old_state
        
    threading.Thread(target=background_timer, daemon=True).start()
    return f"Right away, sir. I have set a timer for {amount} {unit}."