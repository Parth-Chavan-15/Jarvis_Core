import pyttsx3
import threading
import queue
import logging
import pythoncom
import urllib.request
import agent.state as state

logger = logging.getLogger(__name__)

# Create a dedicated, permanent pipeline for audio messages
audio_queue = queue.Queue()

def check_ollama_local():
    """Silent local check to prevent the voice engine from forcing a false idle state."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.getcode() == 200
    except Exception:
        return False

def _voice_worker():
    """A permanent background thread dedicated solely to Windows Audio COM."""
    # Tell Windows this permanent thread is allowed to use the audio drivers
    pythoncom.CoInitialize()

    while True:
        # 1. Wait here silently until a message is dropped into the queue
        text = audio_queue.get()
        
        # 2. Reset the interrupt switch and tell the UI we are speaking
        state.stop_voice = False
        state.current_state = "speaking"

        try:
            # 3. Initialize a fresh engine for each sentence (This prevents the .stop() bug!)
            engine = pyttsx3.init()
            current_rate = engine.getProperty('rate')
            engine.setProperty('rate', current_rate - 15)

            def on_word(name, location, length):
                if state.stop_voice:
                    logger.info("Voice interrupted by system.")
                    engine.stop()

            engine.connect('started-word', on_word)
            
            engine.say(text)
            engine.runAndWait()
            
            # 4. Safely delete the engine instance so memory is clean for the next command
            del engine
            
        except Exception as e:
            logger.error(f"Voice Engine Error: {e}")
        finally:
            if state.current_state == "speaking":
                # THE FIX: Dynamically revert to the correct state based on Ollama's actual status
                state.current_state = "idle" if check_ollama_local() else "ollama_error"
            
            # Tell the queue the task is complete
            audio_queue.task_done()

# Boot up the permanent audio worker thread exactly ONCE when the server starts
worker_thread = threading.Thread(target=_voice_worker, daemon=True)
worker_thread.start()


def speak_text(text: str):
    """
    Takes a string of text and pushes it to the immortal audio queue.
    Does not freeze the FastAPI server.
    """
    audio_queue.put(text)