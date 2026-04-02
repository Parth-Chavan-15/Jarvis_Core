import json
import logging
from ollama import AsyncClient
import agent.state as state
import agent.tools as tools
import agent.eyes as eyes 
from agent.brain import ask_jarvis 

logger = logging.getLogger(__name__)

async def process_interaction(user_message: str) -> str:
    if state.pending_action is not None:
        return await handle_confirmation(user_message)
    return await extract_and_route(user_message)

async def extract_and_route(user_message: str) -> str:
    # THE FIX: Strip punctuation that Whisper automatically adds!
    clean_msg = user_message.lower().strip(" .?!")
    
    # 1. VISION OVERRIDES (Instant Camera)
    vision_triggers = [
        "what is this", "what's this", "what am i holding", 
        "look at this", "what do you see", "describe this"
    ]
    if any(trigger in clean_msg for trigger in vision_triggers):
        state.vision_prompt = user_message 
        return "Accessing optic sensor. One moment, sir..."

    # 2. FAST-TRACK APP LAUNCHER (Instant Speed - Bypasses LLM!)
    if clean_msg.startswith("open ") or clean_msg.startswith("launch "):
        # SAFETY NET: If they ask a question using question words, let Llama 3 handle it!
        question_words = ["meaning", "what", "who", "how", "why"]
        if any(q_word in clean_msg for q_word in question_words):
            pass # Skip this block and let Llama 3 process the question
        else:
            app_name = clean_msg.replace("open ", "").replace("launch ", "").strip()
            if len(app_name.split()) < 3: 
                return tools.execute_open_app(app_name)

    # 3. STRICT FAST-TRACK UTILITIES (Time, Date, Timers - Works Offline!)
    # EXACT MATCH ONLY: "What is the time in Japan" will fail this and go to LLM.
    time_triggers = ["what is the time", "what time is it", "current time", "tell me the time", "what is the system time"]
    if clean_msg in time_triggers:
        return tools.get_time()
        
    date_triggers = ["what is the date", "what is today's date", "what's the date"]
    if clean_msg in date_triggers:
        return tools.get_date()
        
    if "timer for" in clean_msg or "alarm for" in clean_msg:
        try:
            words = clean_msg.split()
            amount = int([w for w in words if w.isdigit()][0])
            unit = "seconds" if "second" in clean_msg else "minutes" if "minute" in clean_msg else "hours"
            return tools.start_timer(amount, unit)
        except Exception:
            pass # If the user speaks weirdly, let the LLM handle it natively

    # 4. LET LLAMA 3 DECIDE EVERYTHING ELSE
    client = AsyncClient()
    system_prompt = """You are an intent extraction engine. Extract the user's intent and output ONLY valid JSON.
    Possible intents: "create_folder", "delete_item", "rename_item", "get_time", "none".
    If create_folder: extract "folder_name" and "target_directory" (default to "desktop").
    If delete_item: extract "item_name" and "target_directory" (default to "desktop").
    If rename_item: extract "old_name", "new_name", and "target_directory" (default to "desktop").
    
    If the user is just asking a general question, conversing, or asking for the meaning of a word, use "none".
    Format: {"intent": "...", "parameters": {"key": "value"}}"""

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
        intent = data.get("intent", "none")
        params = data.get("parameters", {})

        if intent == "create_folder":
            folder_name = params.get("folder_name", "New Folder")
            target_dir = params.get("target_directory", "desktop")
            state.pending_action = {"action": "create_folder", "folder_name": folder_name, "target_directory": target_dir}
            return f"Sir, I am preparing to create a folder named '{folder_name}' in your {target_dir}. Shall I proceed?"

        elif intent == "delete_item":
            item_name = params.get("item_name", "")
            target_dir = params.get("target_directory", "desktop")
            state.pending_action = {"action": "delete_item", "item_name": item_name, "target_directory": target_dir}
            return f"WARNING: You have requested to delete '{item_name}' from your {target_dir}. Are you absolutely sure?"

        elif intent == "rename_item":
            old_name = params.get("old_name", "")
            new_name = params.get("new_name", "")
            target_dir = params.get("target_directory", "desktop")
            state.pending_action = {"action": "rename_item", "old_name": old_name, "new_name": new_name, "target_directory": target_dir}
            return f"Sir, I am preparing to rename '{old_name}' to '{new_name}' in your {target_dir}. Confirm?"

        elif intent == "get_time":
            return tools.get_time()

        else:
            return await ask_jarvis(user_message)

    except Exception as e:
        logger.error(f"Intent Parser Error: {e}")
        # If Ollama is offline, explicitly notify the user gracefully instead of failing silently.
        if "Connection refused" in str(e) or "Timeout" in str(e):
            return "Sir, my neural engine is currently offline. I can only perform basic system tasks right now."
        return await ask_jarvis(user_message)

async def handle_confirmation(user_message: str) -> str:
    client = AsyncClient()
    system_prompt = f"""The user is reviewing this pending task: {json.dumps(state.pending_action)}.
    Analyze the user's reply. Output ONLY valid JSON with a "status" key.
    If user agrees/confirms -> {{"status": "confirmed"}}
    If user cancels/denies -> {{"status": "cancelled"}}
    If user modifies the task parameters -> {{"status": "modified", "new_parameters": {{...}}}}"""

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
            state.pending_action = None 
            
            if action["action"] == "create_folder":
                return tools.execute_create_folder(action["folder_name"], action["target_directory"])
            elif action["action"] == "delete_item":
                return tools.execute_delete_item(action["item_name"], action["target_directory"])
            elif action["action"] == "rename_item":
                return tools.execute_rename_item(action["old_name"], action["new_name"], action["target_directory"])
            
            return "Task confirmed and executed."

        elif status == "modified":
            new_params = data.get("new_parameters", {})
            for key, value in new_params.items():
                if key in state.pending_action:
                    state.pending_action[key] = value
            return f"Understood. I have updated the task parameters. Shall I proceed?"

        else:
            state.pending_action = None 
            return "Task cancelled, sir. Awaiting your next command."

    except Exception as e:
        logger.error(f"Confirmation Error: {e}")
        state.pending_action = None
        return "Confirmation failed due to processing error. Task aborted."