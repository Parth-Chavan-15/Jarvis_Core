import pyttsx3
import threading
import logging
import agent.state as state

logger = logging.getLogger(__name__)

def speak_text(text: str):
    """
    Takes a string of text and speaks it out loud.
    Runs in a background thread so it doesn't freeze the FastAPI server.
    """
    # Reset the kill switch before speaking
    state.stop_voice = False
    state.current_state = "speaking" # Tell the mic to stay deaf

    def _speak_task(spoken_text):
        try:
            # Initialize the TTS engine
            engine = pyttsx3.init()
            current_rate = engine.getProperty('rate')
            engine.setProperty('rate', current_rate - 15) 
            
            # THE FIX: Native Interrupt Hook
            # This hidden function fires automatically right before every single word is spoken
            def on_word(name, location, length):
                if state.stop_voice:
                    logger.info("Voice interrupted by UI.")
                    engine.stop() # Instantly flushes the audio queue and stops talking
            
            # Attach our hook to the engine
            engine.connect('started-word', on_word)
            
            # Queue the ENTIRE paragraph at once (prevents the Windows looping crash)
            engine.say(spoken_text)
            engine.runAndWait()
            
        except Exception as e:
            logger.error(f"Voice Engine Error: {e}")
        finally:
            # Once he finishes (or is interrupted), reset the system state
            if state.current_state == "speaking":
                state.current_state = "idle"

    # Launch it in a parallel thread
    thread = threading.Thread(target=_speak_task, args=(text,), daemon=True)
    thread.start()