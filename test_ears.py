import logging
from agent.ears import wait_for_wake_word, record_and_transcribe

# NEW FIX: Turn on the console logs for this test script
logging.basicConfig(level=logging.INFO, format="%(message)s")

def test_loop():
    print("\n=== JARVIS EARS DIAGNOSTIC ===")
    
    # 1. Start the zero-CPU watchdog
    wake_detected = wait_for_wake_word()
    
    if wake_detected:
        print("\n[SYSTEM] Waking up main AI...")
        
        # 2. Record the actual command
        command = record_and_transcribe()
        
        print(f"\n[FINAL OUTPUT] You asked Jarvis to: {command}")
        print("Diagnostic Complete.")

if __name__ == "__main__":
    test_loop()