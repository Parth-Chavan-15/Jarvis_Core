import speech_recognition as sr

def run_audio_diagnostic():
    print("=== JARVIS AUDIO HARDWARE DIAGNOSTIC ===")
    
    # 1. Scan and print all connected microphones
    print("\nScanning for available microphones...")
    mic_list = sr.Microphone.list_microphone_names()
    
    if not mic_list:
        print("[❌ ERROR] No microphones detected by the system.")
        return

    for index, name in enumerate(mic_list):
        print(f"[{index}] {name}")

    print("\nInitializing default microphone...")
    recognizer = sr.Recognizer()

    try:
        # 2. Open the audio stream
        with sr.Microphone() as source:
            print("[SYSTEM] Microphone active.")
            print("[SYSTEM] Calibrating for background noise... (Please stay quiet for 2 seconds)")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print("\n[🎙️ RECORDING] Please speak a few words out loud now...")
            
            # 3. Wait for the user to speak (timeout if they don't say anything)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            # 4. Success check
            print("\n[✅ SUCCESS] Audio waveform successfully captured!")
            print(f"[SYSTEM] Captured {len(audio.get_raw_data())} bytes of raw audio data.")
            print("Your hardware is fully ready for AI transcription.")
            
    except sr.WaitTimeoutError:
        print("\n[⚠️ WARNING] Listening timed out. The microphone works, but I didn't hear any speech. Check your mic volume.")
    except Exception as e:
        print(f"\n[❌ CRITICAL ERROR] Hardware failure while accessing microphone: {e}")

if __name__ == "__main__":
    run_audio_diagnostic()