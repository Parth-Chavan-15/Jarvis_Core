# agent/state.py
current_state = "idle"  # States: 'idle', 'listening', 'processing', 'speaking'
stop_voice = False      # The kill switch for the UI Interrupt button
voice_logs = []         # Stores voice conversations to send to the Web UI

# Holds the system command while waiting for user confirmation
pending_action = None     # Example: {"action": "create_folder", "folder_name": "Test", "dir": "Desktop"}

# Tells the UI to snap a photo for the LLM
vision_prompt = None

interrupt_llm = False   # The Kill Switch for the LLM generation
cancel_listening = False # NEW: Tells the ears to instantly delete the audio