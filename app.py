import threading
import time
import socket
import sys
import os
import uvicorn
import webbrowser
import subprocess
import atexit
import shutil

DEFAULT_PORT = 8920
HOST = "127.0.0.1"

def find_available_port(start_port: int = DEFAULT_PORT) -> int:
    for p in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((HOST, p)) != 0:
                return p
    return start_port

PORT = find_available_port(DEFAULT_PORT)
URL = f"http://{HOST}:{PORT}"

ollama_process = None

def find_ollama_bin() -> str:
    # Common paths for ollama
    candidates = [
        shutil.which("ollama"),
        "/opt/homebrew/bin/ollama",
        "/usr/local/bin/ollama",
        "/Applications/Ollama.app/Contents/Resources/ollama"
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return ""

def is_ollama_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", 11434)) == 0

def start_ollama_if_needed():
    global ollama_process
    if is_ollama_running():
        # Already running externally
        return

    bin_path = find_ollama_bin()
    if not bin_path:
        print("[Ayna] Ollama ikili dosyası bulunamadı.")
        return

    try:
        print(f"[Ayna] Ollama servisi başlatılıyor: {bin_path} serve")
        ollama_process = subprocess.Popen(
            [bin_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Give it a second to bind port
        for _ in range(15):
            if is_ollama_running():
                print("[Ayna] Ollama servisi hazır.")
                break
            time.sleep(0.2)
    except Exception as e:
        print(f"[Ayna] Ollama başlatılamadı: {e}")

def stop_ollama():
    global ollama_process
    if ollama_process:
        print("[Ayna] Uygulama kapandı: Ollama arka plan süreci temizleniyor...")
        try:
            ollama_process.terminate()
            ollama_process.wait(timeout=3)
        except Exception:
            try:
                ollama_process.kill()
            except Exception:
                pass
        ollama_process = None
        print("[Ayna] Arka plan tamamen temizlendi (0 RAM).")

# Register cleanup on any exit
atexit.register(stop_ollama)

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) == 0

def start_server():
    from server import app
    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="warning")
    server = uvicorn.Server(config)
    server.run()

def open_window():
    # Wait until server is listening
    for _ in range(30):
        if is_port_in_use(PORT):
            break
        time.sleep(0.1)

    print(f"[Ayna] Ayna açılıyor: {URL}")

    # Try pywebview first for 100% native Cocoa/WebKit desktop app experience
    try:
        import webview
        window = webview.create_window(
            title="Ayna — Radikal Dürüstlük & Kişisel Gerçeklik",
            url=URL,
            width=1240,
            height=840,
            min_size=(960, 680),
            background_color="#0b0d11",
            text_select=True
        )
        webview.start()
        # When webview exits:
        stop_ollama()
        return
    except Exception as e:
        print(f"[Ayna] pywebview başlatılamadı ({e}), alternatif başlatıcıya geçiliyor...")

    # Fallback 1: Google Chrome App Mode
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        try:
            p = subprocess.Popen([chrome_path, f"--app={URL}"])
            p.wait()
            stop_ollama()
            return
        except Exception:
            pass

    # Fallback 2: Default browser
    webbrowser.open(URL)

def main():
    # 1. Start Ollama on demand (only while app is open)
    start_ollama_if_needed()

    # 2. Start local FastAPI server
    if not is_port_in_use(PORT):
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()
    
    # 3. Open desktop window
    open_window()

if __name__ == "__main__":
    try:
        main()
    finally:
        stop_ollama()
