import logging
import threading
import asyncio
import os
import time
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from agent.ears import wait_for_wake_word, record_and_transcribe
from agent.voice import speak_text
import agent.state as state
from agent.intent import process_interaction 

# Fixes the Windows asyncio event loop crash logs
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str

def jarvis_audio_loop():
    logger.info("🎙️ Audio AI Systems Online. Running in background...")
    while True:
        while state.current_state == "speaking":
            time.sleep(0.5)

        if state.pending_action is not None:
            logger.info("Awaiting user confirmation. Bypassing wake word...")
            time.sleep(0.5) 
            is_awake = True
        else:
            is_awake = wait_for_wake_word()

        if is_awake:
            command = record_and_transcribe()
            
            if command:
                clean_cmd = command.lower()
                
                # THE FIX: Flexible Substring Matching
                # This will catch "shut down", "shutdown", "please turn off", "exit code", etc.
                if any(phrase in clean_cmd for phrase in ["shutdown", "shut down", "turn off", "exit core", "exit code"]):
                    speak_text("Shutting down core systems. Goodbye.")
                    time.sleep(3) 
                    os._exit(0)   
                
                logger.info(f"Processing Voice Command: {command}")
                reply = asyncio.run(process_interaction(command))
                
                state.voice_logs.append({"user": command, "jarvis": reply})
                speak_text(reply)
            else:
                if state.pending_action is not None:
                    logger.warning("User stayed silent. Aborting pending task.")
                    state.pending_action = None
                    speak_text("Task aborted due to silence. Returning to standby.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    audio_thread = threading.Thread(target=jarvis_audio_loop, daemon=True)
    audio_thread.start()
    yield
    logger.info("Shutting down Jarvis Core Systems...")

def create_app() -> FastAPI:
    app = FastAPI(title="Jarvis Core System", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    @app.post("/api/chat")
    async def chat_endpoint(request: ChatRequest):
        state.stop_voice = True 
        
        clean_cmd = request.message.lower()
        
        # THE FIX: Apply the same flexible matching to the text box
        if any(phrase in clean_cmd for phrase in ["shutdown", "shut down", "turn off", "exit core", "exit code"]):
            speak_text("Shutting down core systems. Goodbye.")
            time.sleep(3)
            os._exit(0)

        state.current_state = "processing"
        reply = await process_interaction(request.message)
        speak_text(reply)
        return {"reply": reply}

    @app.get("/api/status")
    def get_status():
        logs = state.voice_logs.copy()
        state.voice_logs.clear() 
        return {"state": state.current_state, "logs": logs}

    @app.post("/api/stop")
    def stop_audio():
        state.stop_voice = True
        if state.current_state == "speaking":
            state.current_state = "idle"
        return {"status": "stopped"}

    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
    return app

app = create_app()

if __name__ == "__main__":
    logger.info("Booting up Jarvis Core System...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, access_log=False)