"""
VisionMate AI — Start Script
Convenient single-command start for Windows (alternative to start.bat)
"""
import os
import sys
import subprocess
import webbrowser
import time


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)

    print("\n" + "="*50)
    print("  VisionMate AI — Starting up")
    print("="*50 + "\n")

    # Check Flask is installed
    try:
        import flask  # noqa
    except ImportError:
        print("[*] Installing dependencies, please wait...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("[+] Opening browser at http://127.0.0.1:5000")
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

    print("[+] Starting Flask server...\n")
    from app import app
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)


if __name__ == "__main__":
    main()
