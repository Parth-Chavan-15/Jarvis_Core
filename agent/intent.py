# agent/intent.py
import json
import logging
from ollama import AsyncClient
import agent.state as state
import agent.tools as tools
from agent.brain import ask_jarvis # We import your untouched brain here!

logger = logging.getLogger(__name__)

async def process_interaction(user_message: str) -> str:
    """The Master Traffic Cop. Routes to Confirmation, Intent Parser, or normal Brain."""
    
    # 1. Are we currently waiting for a Yes/No/Edit confirmation?
    if state.pending_action is not None:
        return await handle_confirmation(user_message)

    # 2. If not, analyze the intent of the new command
    return await extract_and_route(user_message)

async def extract_and_route(user_message: str) -> str:
    client = AsyncClient()
    # A hidden prompt that forces Llama to output raw JSON data
    system_prompt = """You are an intent extraction engine. Extract the user's intent and output ONLY valid JSON.
    Possible intents: "create_folder", "open_app", "get_time", "none".
    If create_folder: extract "folder_name" and "target_directory" (default to "desktop").
    If open_app: extract "app_name".
    Format: {"intent": "...", "parameters": {"folder_name": "...", "target_directory": "..."}}"""

    try:
        response = await client.chat(
            model='llama3',
            format='json', # This physically forces the AI to output JSON instead of text
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ]
        )
        data = json.loads(response['message']['content'])
        intent = data.get("intent", "none")
        params = data.get("parameters", {})

        # Route the JSON data
        if intent == "create_folder":
            folder_name = params.get("folder_name", "New Folder")
            target_dir = params.get("target_directory", "desktop")
            # Save the task to memory instead of executing it
            state.pending_action = {"action": "create_folder", "folder_name": folder_name, "target_directory": target_dir}
            return f"Sir, I am preparing to create a folder named '{folder_name}' in your {target_dir}. Shall I proceed?"

        elif intent == "open_app":
            app_name = params.get("app_name", "")
            return tools.execute_open_app(app_name) # Apps are safe, just open them without confirmation

        elif intent == "get_time":
            return tools.get_time()

        else:
            # If it's a general question, pass it to your original brain.py
            return await ask_jarvis(user_message)

    except Exception as e:
        logger.error(f"Intent Parser Error: {e}")
        return await ask_jarvis(user_message) # Fallback to normal brain on error

async def handle_confirmation(user_message: str) -> str:
    """Uses LLM to understand if the user said yes, no, or gave a correction."""
    client = AsyncClient()
    system_prompt = f"""The user is reviewing this pending task: {json.dumps(state.pending_action)}.
    Analyze the user's reply. Output ONLY valid JSON with a "status" key.
    If user agrees/confirms -> {{"status": "confirmed"}}
    If user cancels/denies -> {{"status": "cancelled"}}
    If user modifies the name/directory -> {{"status": "modified", "new_folder_name": "...", "new_target_directory": "..."}}"""

    try:
        response = await client.chat(
            model='llama3',
            format='json',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ]
        )
        data = json.loads(response['message']['content'])
        status = data.get("status", "cancelled")

        if status == "confirmed":
            action = state.pending_action
            state.pending_action = None # Clear memory
            if action["action"] == "create_folder":
                return tools.execute_create_folder(action["folder_name"], action["target_directory"])
            return "Task confirmed and executed."

        elif status == "modified":
            # Update the memory with the user's corrections
            state.pending_action["folder_name"] = data.get("new_folder_name", state.pending_action["folder_name"])
            state.pending_action["target_directory"] = data.get("new_target_directory", state.pending_action["target_directory"])
            return f"Understood. I have updated the task. Creating '{state.pending_action['folder_name']}' in your {state.pending_action['target_directory']}. Confirm?"

        else:
            state.pending_action = None # Clear memory
            return "Task cancelled, sir. Awaiting your next command."

    except Exception as e:
        logger.error(f"Confirmation Error: {e}")
        state.pending_action = None
        return "Confirmation failed due to processing error. Task aborted."