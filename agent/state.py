# agent/state.py
current_state = "idle"  # States: 'idle', 'listening', 'processing', 'speaking'
stop_voice = False      # The kill switch for the UI Interrupt button
voice_logs = []         # Stores voice conversations to send to the Web UI

# NEW: Holds the system command while waiting for user confirmation
pending_action = None     # Example: {"action": "create_folder", "folder_name": "Test", "dir": "Desktop"}