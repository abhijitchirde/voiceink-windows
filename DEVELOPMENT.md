# VoiceInk for Windows — Development

This guide covers trying the NVIDIA Parakeet transcription models, which are only available when running from source. The release exe (`dist\VoiceInk\VoiceInk.exe`) supports Whisper only.

---

## Running from Source

```bat
run.bat
```

This activates the venv and launches the app. All Parakeet backends only work this way.

---

## Trying Parakeet Models

### Step 1 — Install the backend

With the venv active, install the dependency for your chosen backend:

```bat
# sherpa-onnx — recommended, no PyTorch needed, fast on CPU
pip install sherpa-onnx

# HF Transformers — needs PyTorch (~500 MB)
pip install transformers>=4.47.0 torch torchaudio

# NeMo — requires Python 3.10 or 3.11, Linux-primary, may need WSL2 on Windows
pip install nemo_toolkit[asr] torch
```

Alternatively, use the **Install** button in the yellow banner on the AI Models settings page — it runs the same pip command in the background.

### Step 2 — Restart the app

```bat
run.bat
```

The app checks for installed backends at startup. A restart is required after pip install.

### Step 3 — Download a model

1. Right-click the tray icon → **Settings → AI Models → Local Model**
2. Scroll to the **NVIDIA Parakeet** section
3. Click **Download** on the model you want
4. Once downloaded, click **Set as Default**

**Recommended starting model:** Parakeet 0.6B v2 INT8 (sherpa-onnx) — 661 MB, no PyTorch, works well on CPU.

---

## Notes

- **sherpa-onnx models** — no PyTorch, best for CPU, tested and working
- **HF Transformers models** — needs torch; CUDA GPU recommended for 1.1B
- **NeMo models** — see section below
- Models are stored at `%APPDATA%\VoiceInk\models\parakeet\`
- Click **📂 View storage** on a downloaded model card to open its folder

---

## Using NeMo Models

NeMo has strict requirements and is the hardest backend to get working on Windows. Read this before trying.

### Requirements

| Requirement         | Details                                                   |
| ------------------- | --------------------------------------------------------- |
| **Python version**  | 3.10 or 3.11 only — NeMo does not support 3.12 or 3.13    |
| **C++ Build Tools** | Required to compile `editdistance` (a NeMo dependency)    |
| **PyTorch**         | Required (~500 MB, CUDA build recommended)                |
| **OS**              | NeMo is Linux-primary — Windows works but has rough edges |

### Step 1 — Use Python 3.10 or 3.11

Check your current version:

```bat
python --version
```

If it shows 3.12 or 3.13, you need a separate Python 3.11 installation. Download from [python.org](https://www.python.org/downloads/release/python-3110/). You do not need to uninstall your existing Python — just install 3.11 alongside it.

Then recreate the venv with Python 3.11 explicitly:

```bat
py -3.11 -m venv venv
```

### Step 2 — Install Microsoft C++ Build Tools

NeMo's `editdistance` dependency compiles a C extension. Without Build Tools, pip will fail with:

```text
error: Microsoft Visual C++ 14.0 or greater is required.
```

Download and install **Microsoft C++ Build Tools** from:
[https://visualstudio.microsoft.com/visual-cpp-build-tools/](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

During installation, select **"Desktop development with C++"**. This is a ~6 GB download.

### Step 3 — Install NeMo

With the correct Python (3.10 or 3.11) venv active and Build Tools installed:

```bat
pip install nemo_toolkit[asr] torch
```

For CUDA GPU acceleration, install the CUDA-enabled PyTorch build instead:

```bat
pip install nemo_toolkit[asr]
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

Replace `cu121` with your CUDA version (check with `nvidia-smi`).

### Step 4 — WSL2 (if NeMo still fails on Windows)

NeMo is developed primarily for Linux. Some components (audio processing libraries) may fail to install or run natively on Windows. If you hit errors after Build Tools are installed, WSL2 is the most reliable path:

1. Enable WSL2: `wsl --install` in an admin PowerShell
2. Install Ubuntu from the Microsoft Store
3. Inside Ubuntu: `sudo apt install python3.11 python3.11-venv`
4. Clone the repo inside WSL2 and run `setup.bat` equivalent commands there

### NeMo models available

| Model                | Size   | Notes                                         |
| -------------------- | ------ | --------------------------------------------- |
| Parakeet 110M        | 459 MB | Smallest, CPU-practical                       |
| Parakeet TDT 0.6B v2 | 2.5 GB | CUDA recommended                              |
| Parakeet TDT 0.6B v3 | 2.5 GB | Multilingual (25 languages), CUDA recommended |
| Parakeet TDT 1.1B    | 4.3 GB | Highest accuracy, CUDA required               |

> **Recommendation:** Unless you specifically need NeMo, use the sherpa-onnx backend instead. It has no Python version requirement, no C++ compiler needed, no PyTorch dependency, and works on the same Python 3.13 venv you already have.
