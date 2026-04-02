import sys
import urllib.request
import json
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView

# THE HARDWARE-ACCELERATED HOLOGRAPHIC ORB
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
<style>
    body, html {
        margin: 0; padding: 0; width: 100%; height: 100%;
        background-color: transparent; 
        overflow: hidden;
    }

    #globe-container {
        position: absolute;
        bottom: 50px;
        right: 50px;
        margin-right: 0;
        margin-bottom: 0;
        width: 120px;
        height: 120px;
        transition: all 0.8s cubic-bezier(0.25, 1, 0.5, 1);
        transform-style: preserve-3d;
        perspective: 1000px;
    }

    /* THE STATE MACHINE */
    #globe-container.offline { 
        --theme: #ff3333; /* Danger Red (Main.py is dead) */
        --speed: 10s; 
        opacity: 0.3; 
        transform: scale(0.6); 
    }
    #globe-container.ollama_error { 
        --theme: #2f6bff; /* Cobalt (Ollama is dead) */
        --speed: 8s; 
        opacity: 0.4; 
        transform: scale(0.6); 
    }
    #globe-container.booting { 
        --theme: #a800ff; /* Purple Boot Sequence */
        --speed: 1.5s; 
        opacity: 1; 
        /* Forces the orb to fly to the exact center of the screen */
        bottom: 50%; right: 50%;
        margin-bottom: -60px; margin-right: -60px;
        transform: scale(2.5); 
    }
    #globe-container.idle { 
        --theme: #00f3ff; /* Calm Cyan */
        --speed: 8s; 
        opacity: 0.4; 
        transform: scale(0.6); 
    }
    #globe-container.listening { 
        --theme: #ff0055; /* Siri Pink/Red */
        --speed: 1.5s; 
        opacity: 1; 
        transform: scale(1.1); 
    }
    #globe-container.processing { 
        --theme: #ffbb33; /* Thinking Yellow */
        --speed: 0.8s; 
        opacity: 0.9; 
        transform: scale(0.9); 
    }
    #globe-container.speaking { 
        --theme: #00C851; /* Matrix Green */
        --speed: 2.5s; 
        opacity: 1; 
        transform: scale(1.0); 
    }

    .core {
        position: absolute; inset: 25px; border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #ffffff, var(--theme));
        box-shadow: 0 0 30px var(--theme), inset 0 0 20px #000;
        animation: pulse var(--speed) infinite alternate ease-in-out;
        transition: background 0.5s, box-shadow 0.5s;
    }

    .ring {
        position: absolute; inset: 0; border-radius: 50%;
        border: 2px solid transparent;
        border-top: 3px solid var(--theme); border-bottom: 3px solid var(--theme);
        box-shadow: 0 0 15px var(--theme) inset;
        animation: spin var(--speed) linear infinite;
        transition: border-color 0.5s, box-shadow 0.5s;
    }

    .ring:nth-child(2) { 
        animation: spin-reverse calc(var(--speed) * 1.5) linear infinite; 
        border-top-color: transparent; border-bottom-color: transparent;
        border-left: 3px solid var(--theme); border-right: 3px solid var(--theme); 
        transform: rotateX(60deg); 
    }
    .ring:nth-child(3) { 
        animation: spin-wobble calc(var(--speed) * 1.2) linear infinite; 
        border-top-color: transparent; border-bottom-color: transparent;
        border-right: 3px solid var(--theme); 
        transform: rotateY(60deg); 
    }

    @keyframes spin { 100% { transform: rotate(360deg); } }
    @keyframes spin-reverse { 100% { transform: rotateX(60deg) rotate(-360deg); } }
    @keyframes spin-wobble { 100% { transform: rotateY(60deg) rotate(360deg) rotateX(360deg); } }
    @keyframes pulse { 
        0% { transform: scale(0.85); box-shadow: 0 0 15px var(--theme); } 
        100% { transform: scale(1.15); box-shadow: 0 0 45px var(--theme); } 
    }
</style>
</head>
<body>
    <div id="globe-container" class="offline">
        <div class="ring"></div>
        <div class="ring"></div>
        <div class="ring"></div>
        <div class="core"></div>
    </div>
    <script>
        function setState(state) {
            document.getElementById('globe-container').className = state;
        }
    </script>
</body>
</html>
"""

class SiriHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.browser = QWebEngineView()
        self.browser.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self.browser.setHtml(HTML_CONTENT)
        
        self.setCentralWidget(self.browser)
        self.showFullScreen()
        
        self.current_state = "offline"
        
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.check_server)
        self.poll_timer.start(300)

    def check_server(self):
        try:
            req = urllib.request.Request("http://127.0.0.1:8000/api/hud")
            with urllib.request.urlopen(req, timeout=1) as response:
                data = json.loads(response.read().decode())
                new_state = data["state"]
                
                if new_state != self.current_state:
                    self.current_state = new_state
                    self.browser.page().runJavaScript(f"setState('{new_state}');")
                    
        except Exception:
            if self.current_state != "offline":
                self.current_state = "offline"
                self.browser.page().runJavaScript("setState('offline');")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SiriHUD()
    sys.exit(app.exec())