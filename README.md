# VoiceInk for Windows

A Windows port of [VoiceInk](https://github.com/Beingpax/VoiceInk), the macOS voice transcription app originally built in Swift. This version is rewritten in Python to bring the same functionality to Windows — record audio with a global hotkey, transcribe it locally using Whisper, and paste the result directly into any app.

---

## Features

- Global hotkey to start/stop recording from anywhere
- Local transcription via [faster-whisper](https://github.com/guillaumekynast/faster-whisper) (no audio leaves your machine)
- Optional AI enhancement of transcribed text
- Auto-paste into the active window
- System tray icon for quick access
- Transcription history window

---

## Requirements

- Windows 10 or 11
- Python 3.11 or newer — download from [python.org](https://www.python.org/downloads/)
  - During installation, check **"Add Python to PATH"**
- A microphone

---

## Scripts Overview

| Script      | What it does                                                | When to use                                                    |
| ----------- | ----------------------------------------------------------- | -------------------------------------------------------------- |
| `setup.bat` | Creates a virtual environment and installs all dependencies | Run once after cloning                                         |
| `run.bat`   | Launches the app from source (no build required)            | Day-to-day development and testing                             |
| `build.bat` | Packages the app into a standalone `.exe` using PyInstaller | After `setup.bat`, when you want a distributable build         |
| `make.bat`  | Does everything in one shot: setup + build                  | First-time build or when you want a clean rebuild from scratch |

---

## Getting Started

### 1. Clone the repository

```bat
git clone https://github.com/abhijitchirde/voiceink-windows.git
cd voiceink-windows
```

### 2. Install dependencies

Run `setup.bat` once to create a virtual environment and install all required packages:

```bat
setup.bat
```

This will:

- Create a Python virtual environment under `venv\`
- Upgrade pip
- Install all dependencies from `requirements.txt`

### 3. Run the app

To launch VoiceInk directly from source (no build needed):

```bat
run.bat
```

Use this during development or just to try the app without building an executable.

### 4. Start recording

Once VoiceInk is running, you will see its icon in the system tray. The default hotkey is **Right Ctrl**.

| Action                  | How                                                                          |
| ----------------------- | ---------------------------------------------------------------------------- |
| **Start recording**     | Press Right Ctrl once                                                        |
| **Stop and transcribe** | Press Right Ctrl again (or hold Right Ctrl to record, release to transcribe) |
| **Cancel**              | Click the × on the overlay pill                                              |

The transcribed text is automatically pasted at your cursor.

> **Transcription history:** Right-click the VoiceInk tray icon and choose **History** to browse all your previously transcribed text.

> **Want a different hotkey?** Right-click the VoiceInk tray icon → **Settings**, then change the hotkey and mode to whatever suits you.

---

## Building a Standalone .exe

### Quick build — `make.bat` (recommended for first-time or clean builds)

`make.bat` handles the full pipeline in one command: creates the venv, installs dependencies, and builds the executable. No need to run `setup.bat` separately.

```bat
make.bat
```

### Manual build — `build.bat` (when setup is already done)

If you have already run `setup.bat` and just want to rebuild the executable:

```bat
build.bat
```

The output will be at:

```text
dist\VoiceInk\VoiceInk.exe
```

This `.exe` is fully self-contained — no Python installation is needed on the machine running it.

---

## Transcription — Local Whisper Models

VoiceInk uses [faster-whisper](https://github.com/guillaumekynast/faster-whisper) for local transcription. No audio is sent anywhere — everything runs on your machine.

### Available models

| Model      | Size   | Notes                                        |
| ---------- | ------ | -------------------------------------------- |
| `tiny`     | 75 MB  | Fastest, lowest accuracy                     |
| `base`     | 145 MB | Default — good balance of speed and accuracy |
| `small`    | 466 MB | Better accuracy, slightly slower             |
| `medium`   | 1.5 GB | High accuracy                                |
| `large-v3` | 3 GB   | Best accuracy, slowest                       |

The default model is `base`. You can change this in the app settings.

### Where models are downloaded from

Models are downloaded automatically from Hugging Face (`Systran/faster-whisper-*`) the first time you use them. The app looks for models in this order:

1. `%APPDATA%\VoiceInk\models\<model-name>\` — manually placed models
2. The Hugging Face local cache at `~\.cache\huggingface\hub\` — already downloaded models
3. Automatic download from Hugging Face — if not found locally

You do not need to download anything manually before first run. The selected model will download on first use.

### Common issues

**Download fails or times out**
This usually means a network or firewall issue blocking Hugging Face. You can set a custom cache location using the `HF_HOME` environment variable:

```bat
set HF_HOME=D:\my-models
run.bat
```

**`int8` compute type error on older CPUs**
The app tries `int8` first and automatically falls back to `float32` if your CPU does not support it. No action needed.

**Model loads slowly on first use**
The first load after download takes longer while the model is prepared. Subsequent loads use the cached version and are faster.

---

## GPU Acceleration (Optional)

By default, transcription runs on CPU. If you have an NVIDIA GPU with CUDA installed, uncomment the relevant lines in `requirements.txt` and reinstall:

```text
# torch>=2.0.0
# nvidia-cublas-cu12
# nvidia-cudnn-cu12
```

Then run `setup.bat` again to install the GPU packages.

---

## Roadmap

The following features are not yet implemented but are planned for future versions:

- **Cloud transcription providers** — Groq, OpenAI Whisper API, Deepgram, and custom OpenAI-compatible endpoints are already wired in the codebase but API key configuration via the UI is not yet exposed
- **AI enhancement** — post-transcription cleanup and formatting via OpenAI, Anthropic, Groq, Gemini, Mistral, Cerebras, OpenRouter, or a local Ollama instance is implemented in the backend but the settings UI for configuring API keys is not yet complete
- **Model selector UI** — ability to switch Whisper models from within the app without editing settings manually

---

## Original Project

This is a port of [VoiceInk for macOS](https://github.com/Beingpax/VoiceInk) by [@Beingpax](https://github.com/Beingpax), originally written in Swift. All credit for the concept and original design goes to the original project.

---

## License

This project is licensed under the GNU General Public License v3.0 — see the [LICENSE](LICENSE.txt) file for details.

As a fork of [VoiceInk for macOS](https://github.com/Beingpax/VoiceInk), this project inherits and complies with the original GPL v3 license.

---

Made with ❤️ by Abhijit
