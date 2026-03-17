"""
VoiceInk for Windows — entry point.
Run with:  python main.py
Build exe: python build.py
"""

import sys
import os

# Ensure the project root is on the path when running as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voiceink.app import VoiceInkApp


def main():
    app = VoiceInkApp()
    app.run()


if __name__ == "__main__":
    main()
