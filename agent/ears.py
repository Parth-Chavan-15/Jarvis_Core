import pyaudio
import numpy as np
import speech_recognition as sr
from faster_whisper import WhisperModel
from openwakeword.model import Model
import logging
import os
import time
import agent.state as state

logger = logging.getLogger(__name__)

logger.info("Booting Audio AI Models... (This takes a few seconds)")

oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
whisper_model = WhisperModel("medium.en", device="cpu", compute_type="int8")

def wait_for_wake_word():
    # Do not even open the microphone if Jarvis is NOT idle
    while state.current_state != "idle":
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
            if state.current_state != "idle":
                mic_stream.stop_stream()
                mic_stream.close()
                audio.terminate()
                return False

            pcm = mic_stream.read(CHUNK, exception_on_overflow=False)
            pcm_arr = np.frombuffer(pcm, dtype=np.int16)
            prediction = oww_model.predict(pcm_arr)
            
            if prediction['hey_jarvis'] > 0.75:
                logger.info("⚡ Wake word detected!")
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
    
    # THE FIX 1: Lowered threshold from 300 to 150 to pick up quiet words like "yes"
    recognizer.energy_threshold = 150 
    recognizer.dynamic_energy_threshold = True 
    
    audio_filename = "temp_command.wav"
    
    with sr.Microphone() as source:
        # THE FIX 2: Recalibrate the mic after Jarvis speaks to reset Windows Echo Cancellation
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        state.current_state = "listening" 
        logger.info("🔴 Recording command... (Speak now)")
        
        try:
            # THE FIX 3: Increased timeout to 8 seconds so you don't feel rushed
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            
            state.current_state = "processing" 
            with open(audio_filename, "wb") as f:
                f.write(audio.get_wav_data())
                
            logger.info("Transcribing...")
            
            # THE FIX 4: Force Whisper to recognize common names and short commands!
            segments, _ = whisper_model.transcribe(
                audio_filename, 
                beam_size=5,
                initial_prompt="Yes. No. Confirm. Cancel. Desktop. Documents. Downloads. Parth Chavan."
            )
            transcription = " ".join([segment.text for segment in segments]).strip()
            
            if os.path.exists(audio_filename):
                os.remove(audio_filename)
                
            logger.info(f"User Command: {transcription}")
            return transcription
            
        except sr.WaitTimeoutError:
            logger.warning("Listening timed out. No command heard.")
            state.current_state = "idle" 
            return ""
        except Exception as e:
            logger.error(f"Recording Error: {e}")
            state.current_state = "idle" 
            return ""