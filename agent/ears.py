import pyaudio
import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel
from openwakeword.model import Model
import logging
import os
import time
import urllib.request
import agent.state as state

logger = logging.getLogger(__name__)

logger.info("Booting Audio AI Models... (This takes a few seconds)")

# Dynamically locate the custom models folder in your project
current_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(current_dir, "..", "models", "hey_jarvis_v0.1.onnx")

# Load the custom file using wakeword_model_paths instead of wakeword_models
oww_model = Model(wakeword_model_paths=[model_path], inference_framework="onnx")
whisper_model = WhisperModel("medium.en", device="cuda", compute_type="int8")

def check_ollama_local():
    """Silent local check to prevent the state-reset loop."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/")
        with urllib.request.urlopen(req, timeout=1) as response:
            return response.getcode() == 200
    except Exception:
        return False

def play_chime():
    """Generates a pleasant, Google-Assistant style double-chime over main speakers."""
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True)
        
        # Generate two tones: C5 (523.25 Hz) and E5 (659.25 Hz)
        t1 = np.linspace(0, 0.15, int(44100 * 0.15), False)
        t2 = np.linspace(0, 0.25, int(44100 * 0.25), False)
        
        tone1 = np.sin(523.25 * 2 * np.pi * t1) * 0.3 # 30% volume
        tone2 = np.sin(659.25 * 2 * np.pi * t2) * 0.3
        
        # Smooth fade out on the second note
        tone2 = tone2 * np.linspace(1, 0, len(tone2))
        
        audio_data = np.concatenate((tone1, tone2)).astype(np.float32)
        stream.write(audio_data.tobytes())
        
        stream.stop_stream()
        stream.close()
        p.terminate()
    except Exception as e:
        logger.error(f"Failed to play chime: {e}")

def wait_for_wake_word():
    # THE FIX: Allow the ears to listen even if Ollama is offline
    while state.current_state not in ["idle", "ollama_error"]:
        time.sleep(0.5)

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1280
    
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    for _ in range(15):
        mic_stream.read(CHUNK, exception_on_overflow=False)
        
    oww_model.predict(np.zeros(24000, dtype=np.int16))
    if hasattr(oww_model, 'reset'):
        oww_model.reset()
    
    logger.info("🟢 System Online: Waiting for 'Hey Jarvis'...")
    
    try:
        while True:
            # THE FIX: Allow the loop to continue if state is idle OR ollama_error
            if state.current_state not in ["idle", "ollama_error"]:
                mic_stream.stop_stream()
                mic_stream.close()
                audio.terminate()
                return False

            pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
            pcm_arr = np.frombuffer(pcm, dtype=np.int16)
            prediction = oww_model.predict(pcm_arr)
            
            if prediction['hey_jarvis_v0.1'] > 0.75:
                logger.info("⚡ Wake word detected!")
                play_chime()
                mic_stream.stop_stream()
                mic_stream.close()
                audio.terminate()
                return True
    except KeyboardInterrupt:
        logger.info("Shutting down hotword engine.")
        return False
    
def record_and_transcribe() -> str:
    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.2 
    recognizer.energy_threshold = 150 
    recognizer.dynamic_energy_threshold = True 
    audio_filename = "temp_command.wav"
    
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        state.current_state = "listening" 
        logger.info("🔴 Recording command... (Speak now)")
        
        try:
            # Reset the kill switch before we start
            state.cancel_listening = False 
            
            # Increased timeout to 8 seconds
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            
            # THE FIX: Did the user hit STOP while we were listening?
            if state.cancel_listening:
                logger.info("Recording deleted. User interrupted.")
                state.cancel_listening = False
                state.current_state = "idle" if check_ollama_local() else "ollama_error"
                return "" # Return empty string so the brain does nothing!
            
            state.current_state = "processing" 
            with open(audio_filename, "wb") as f:
                f.write(audio.get_wav_data())
                
            logger.info("Transcribing...")
            
            # Force Whisper to recognize common names and short commands!
            segments, _ = whisper_model.transcribe(
                audio_filename, 
                beam_size=5,
                initial_prompt="Yes. No. Confirm. Cancel. Shut down. Desktop. Documents. Downloads. Parth Chavan."
            )
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            if os.path.exists(audio_filename):
                os.remove(audio_filename)
                
            logger.info(f"User Command: {transcription}")
            return transcription
            
        except sr.WaitTimeoutError:
            logger.warning("Listening timed out. No command heard.")
            state.current_state = "idle" if check_ollama_local() else "ollama_error"
            return ""
        except Exception as e:
            logger.error(f"Recording Error: {e}")
            state.current_state = "idle" if check_ollama_local() else "ollama_error"
            return ""