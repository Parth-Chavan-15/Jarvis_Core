# Jarvis Core 

An autonomous, voice-controlled AI agent powered by Llama 3, Faster-Whisper, and OpenWakeWord.

## ⚠️ System Requirements
1. **Windows OS** (Tools are configured for Windows paths and executables).
2. **Python 3.10** (Crucial: `PyAudio` installs cleanly on 3.10. Newer versions may require Visual Studio C++ Build Tools).

## 🚀 How to Clone and Run on a New PC

### 1. Install Ollama (The Brain Engine)
Because Jarvis uses Llama 3 running locally, you must install the engine first.
* Download and install from [Ollama.com](https://ollama.com/)
* Open your command prompt and run: 
  `ollama run llama3`
* *(Wait for the model to download. Once it allows you to chat, type `/bye` to exit).*

### 2. Setup the Python Environment
Open your terminal in the cloned folder and run these commands to isolate the dependencies:
```bash
python -m venv venv
venv\Scripts\activate

### 3. Install the AI Libraries
```bash
pip install -r requirements.txt

### 4. Boot Up Jarvis
```bash
python main.py