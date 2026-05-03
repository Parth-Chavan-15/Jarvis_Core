import logging
import threading
import asyncio
import os
import time
import sys
import subprocess
import urllib.request
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

import pystray
from PIL import Image, ImageDraw

from agent.ears import wait_for_wake_word, record_and_transcribe
from agent.voice import speak_text
import agent.state as state
from agent.intent import process_interaction 

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

overlay_process = None

class ChatRequest(BaseModel):
    message: str

class VisionRequest(BaseModel):
    prompt: str
    image_b64: str

class VisionErrorRequest(BaseModel):
    error: str

def shutdown_jarvis():
    logger.info("Initiating core shutdown sequence...")
    state.current_state = "booting" # Pulls Orb to the center & turns Purple
    time.sleep(1.5) # Give the UI time to glide to the center
    
    state.current_state = "speaking" # Turn Green while saying goodbye
    speak_text("Shutting down core systems. Goodbye.")
    
    # THE FIX: Increased sleep from 1s to 4s to let the voice finish speaking!
    time.sleep(4.5) 
    
    if overlay_process is not None:
        overlay_process.terminate()
    os._exit(0)

def create_tray_icon():
    def on_quit(icon, item):
        icon.stop()
        shutdown_jarvis()

    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((4, 4, 60, 60), fill=(0, 243, 255, 255)) 

    icon = pystray.Icon("Jarvis", image, "Jarvis Core AI", menu=pystray.Menu(
        pystray.MenuItem("Exit Jarvis", on_quit)
    ))
    icon.run()

# --- THE SELF-AWARENESS SYSTEMS ---

def check_ollama():
    """Silently pings Ollama to see if it is running."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.getcode() == 200
    except Exception:
        return False

def ollama_monitor():
    """A permanent background thread that checks Ollama every 3 seconds."""
    while True:
        time.sleep(3)
        # Only intervene if Jarvis isn't busy doing something else
        if state.current_state in ["idle", "ollama_error"]:
            is_running = check_ollama()
            
            # If it comes BACK online
            if is_running and state.current_state == "ollama_error":
                state.current_state = "speaking" 
                speak_text("Connection to Ollama neural engine re-established.")
                state.current_state = "idle" 
                
            # THE FIX: If it goes OFFLINE in the middle of a session
            elif not is_running and state.current_state == "idle":
                state.current_state = "speaking" # Turn green to speak
                speak_text("Warning. Connection to the neural engine has been lost.")
                state.current_state = "ollama_error" # Settle on Amber

def startup_sequence():
    """The Hollywood-style Center Screen Boot Sequence"""
    state.current_state = "booting"
    time.sleep(2.5) # Wait for FastAPI to bind and allow orb to center
    
    # 2. Check Ollama
    is_running = check_ollama()
        
    # 3. Generate Time-Aware Greeting
    current_hour = time.localtime().tm_hour
    if current_hour < 12:
        greeting = "Good morning, sir."
    elif current_hour < 18:
        greeting = "Good afternoon, sir."
    else:
        greeting = "Good evening, sir."
        
    # THE FIX: Turn green to speak, then settle on proper color
    state.current_state = "speaking"
    if is_running:
        speak_text(f"{greeting} All core systems are initialized and online.")
        state.current_state = "idle"
    else:
        speak_text(f"{greeting} Core systems initialized. However, the Ollama neural engine is currently unreachable. Please start it for full functionality.")
        state.current_state = "ollama_error"
        
    # 4. Start the continuous background monitor
    threading.Thread(target=ollama_monitor, daemon=True).start()

# ----------------------------------

def jarvis_audio_loop():
    logger.info("🎙️ Audio AI Systems Online. Running in background...")
    while True:
        while state.current_state == "speaking":
            time.sleep(0.5)

        if state.pending_action is not None:
            time.sleep(0.5) 
            is_awake = True
        else:
            is_awake = wait_for_wake_word()

        if is_awake:
            # THE FIX: Kill the voice engine and clear the queue the moment he wakes up!
            state.stop_voice = True 
            import agent.voice as voice
            with voice.audio_queue.mutex:
                voice.audio_queue.queue.clear()
                
            command = record_and_transcribe()
            if command:
                clean_cmd = command.lower()
                if any(phrase in clean_cmd for phrase in ["shutdown", "shut down", "turn off", "exit core", "exit code"]):
                    shutdown_jarvis()
                
                state.interrupt_llm = False 
                state.current_state = "processing" # Yellow while intent logic runs
                reply = asyncio.run(process_interaction(command))
                
                if not state.interrupt_llm:
                    state.voice_logs.append({"user": command, "jarvis": reply})
                    state.current_state = "speaking" # Green while speaking
                    speak_text(reply)
                    
                    # Revert to the correct state, not blindly to cyan
                    is_running = check_ollama()
                    state.current_state = "idle" if is_running else "ollama_error"
        else:
            if state.pending_action is not None:
                state.pending_action = None
                state.current_state = "speaking"
                speak_text("Task aborted due to silence. Returning to standby.")
                
                is_running = check_ollama()
                state.current_state = "idle" if is_running else "ollama_error"

@asynccontextmanager
async def lifespan(app: FastAPI):
    global overlay_process
    threading.Thread(target=create_tray_icon, daemon=True).start()
    overlay_process = subprocess.Popen([sys.executable, "overlay.py"])
    threading.Thread(target=jarvis_audio_loop, daemon=True).start()
    threading.Thread(target=startup_sequence, daemon=True).start()
    yield
    if overlay_process:
        overlay_process.terminate()

def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis Core System", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.post("/api/chat")
    async def chat_endpoint(request: ChatRequest):
        state.stop_voice = True 
        clean_cmd = request.message.lower()
        if any(phrase in clean_cmd for phrase in ["shutdown", "shut down", "turn off", "exit core"]):
            shutdown_jarvis()

        state.current_state = "processing"
        state.interrupt_llm = False
        reply = await process_interaction(request.message)
        
        if not state.interrupt_llm:
            state.current_state = "speaking" # Turn green
            speak_text(reply)
            
            # Revert dynamically
            is_running = check_ollama()
            state.current_state = "idle" if is_running else "ollama_error"
            return {"reply": reply}
        else:
            return {"reply": "... [Interrupted]"}

    @app.post("/api/vision")
    async def vision_endpoint(request: VisionRequest):
        import agent.eyes as eyes
        from agent.voice import speak_text 
        
        state.current_state = "processing"
        speak_text("Image captured. Analyzing visual data...")
        clean_b64 = request.image_b64.split(",")[1] if "," in request.image_b64 else request.image_b64
        state.interrupt_llm = False
        reply = await eyes.analyze_image(request.prompt, clean_b64)
        
        if not state.interrupt_llm:
            state.voice_logs.append({"user": f"📷 [Vision Request]: {request.prompt}", "jarvis": reply})
            state.current_state = "speaking"
            speak_text(reply)
            
            is_running = check_ollama()
            state.current_state = "idle" if is_running else "ollama_error"
            return {"reply": reply}
        else:
            return {"reply": "... [Interrupted]"}
        
    @app.post("/api/vision_failed")
    def vision_failed_endpoint(request: VisionErrorRequest):
        from agent.voice import speak_text
        warning = "Sir, I cannot access the optic sensor. Please ensure the command center browser is active and visible on your screen."
        state.voice_logs.append({"user": "📷 [Vision Request Failed]", "jarvis": warning})
        
        state.current_state = "speaking"
        speak_text(warning)
        
        is_running = check_ollama()
        state.current_state = "idle" if is_running else "ollama_error"
        return {"status": "warning_issued"}

    @app.get("/api/status")
    def get_status():
        logs = state.voice_logs.copy()
        state.voice_logs.clear() 
        vision_trigger = state.vision_prompt
        state.vision_prompt = None 
        return {
            "state": state.current_state, 
            "logs": logs,
            "vision_prompt": vision_trigger 
        }
    
    @app.get("/api/hud")
    def get_hud_status():
        return {"state": state.current_state}

    @app.post("/api/stop")
    def stop_audio():
        state.stop_voice = True
        state.interrupt_llm = True 
        state.cancel_listening = True 
        import agent.voice as voice
        with voice.audio_queue.mutex:
            voice.audio_queue.queue.clear()
            
        is_running = check_ollama()
        state.current_state = "idle" if is_running else "ollama_error"
        return {"status": "stopped"}

    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, access_log=False)