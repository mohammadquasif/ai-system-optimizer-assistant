# ⚡ AI System Optimizer Assistant

<div align="center">

![AI System Optimizer](https://img.shields.io/badge/AI%20System%20Optimizer-v1.0.0-00D4FF?style=for-the-badge&logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-0.5b%20to%201.5b-black?style=for-the-badge)
![License](https://img.shields.io/badge/License-Personal%20Use-00FF88?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=for-the-badge&logo=windows)

**One-click AI-powered Windows optimizer.**  
*Auto Cleanup • Local AI • Voice Commands • Chip UI • On-Demand Only — Zero Background RAM*

**by [Mohammad Quasif, DBA (AI)](https://github.com/mohammadquasif)**

</div>

---

## 🧠 What Is This?

The **AI System Optimizer Assistant** is a free, privacy-first desktop app that:

- 🤖 **Installs Ollama automatically** — no manual setup needed
- 🧹 **Cleans your PC safely** — 12+ cleanup tasks, never touches personal files
- 📊 **Monitors system health** in real time — CPU, RAM, Disk gauges
- 🎙️ **Greets you by voice** on startup, listens to spoken commands
- 💬 **Chat-style chip UI** — click chips, type, or speak to run commands
- 💤 **Auto-closes after 5 minutes idle** — frees RAM when you are not using it
- 🌐 **Works offline** after first setup

---

## 🛠️ Technology Stack

| Technology | Role |
| :--- | :--- |
| **Python 3.11+** | Core language |
| **PyQt6** | Glassmorphism / Cyberpunk UI framework |
| **Ollama** | Local AI engine (offline, private) |
| **psutil** | Real-time CPU / RAM / Disk metrics |
| **pyttsx3** | Offline text-to-speech voice assistant |
| **SpeechRecognition** | Voice command input |
| **SQLite + Fernet** | Encrypted local settings storage |
| **winshell / pywin32** | Windows system integration |

---

## 🤖 AI Models Used (Ultra-Small — Low RAM)

The app **always picks the smallest model** that fits your system. Models are max 1.5b in size.

```
Available RAM → Auto-selected Model
──────────────────────────────────────────────────────────
2 GB+   →  qwen2.5:0.5b  (0.4 GB) ← Ultra-fast, default
2 GB+   →  qwen2.5:1b    (0.8 GB) ← Best quality at 1B
2 GB+   →  llama3.2:1b   (0.9 GB) ← Llama 3.2 quality
3 GB+   →  qwen2.5:1.5b  (1.0 GB) ← Max capability

⚠️  Models above 1.5b are NEVER used — keeps the app fast and light.
```

---

## 🏗️ Project Structure

```text
AI-System-Optimizer/
├── app.py                 # ⚡ Entry Point — Startup, Idle Watcher, Greeting
├── ai/
│   ├── ai_service.py      # 🤖 AI provider abstraction (Ollama / OpenAI)
│   └── ollama_manager.py  # 🔄 Auto-install, model pull, service lifecycle
├── cleanup/
│   └── cleanup_engine.py  # 🧹 12+ Safe cleanup tasks + RAM trim + DNS flush
├── monitoring/
│   └── system_monitor.py  # 📊 Threaded real-time CPU / RAM / Disk metrics
├── services/
│   ├── voice_service.py   # 🎙️ TTS greeting + voice command recognition
│   └── idle_watcher.py    # 💤 5-min idle detector → auto-close → free RAM
├── ui/
│   ├── main_window.py     # 🪟 Main window, sidebar, system tray
│   ├── command_input.py   # 💬 Chip buttons + text input + voice button
│   ├── auto_setup_dialog.py # 🚀 First-launch animated progress wizard
│   ├── widgets.py         # 🎨 Glassmorphism gauges, cards, sparklines
│   └── pages/             # 📄 Dashboard, AI Chat, Cleanup, Performance...
└── config/
    └── settings.py        # ⚙️ SQLite + AES-256 encrypted settings
```

---

## 📋 Prerequisites

> **None. Zero. Nada.**  
> `INSTALL.bat` checks and installs everything automatically.

| Need | Auto-handled By |
| :--- | :--- |
| **Windows 10 / 11** (64-bit) | Required (auto-detected) |
| **Python 3.13** | ✅ Auto-downloaded and installed if missing |
| **Python packages** | ✅ Auto-installed from `requirements.txt` |
| **Ollama** | ✅ Auto-downloaded and installed if missing |
| **AI Model** (0.5b–1.5b) | ✅ Pulled automatically — **skipped if already installed** |
| **Internet** | Needed on first run only (~500 MB total) |

> ✅ After first setup, the app works **100% offline** forever.

---

## 📥 How to Install — 3 Steps for Anyone

### Option A — Download ZIP (Normal Users, No Git)

```
Step 1 → Visit: github.com/mohammadquasif/ai-system-optimizer
         Click the green "Code" button → "Download ZIP"

Step 2 → Right-click the ZIP file → "Extract All" → Open the folder

Step 3 → Double-click "INSTALL.bat"
         (If Windows asks, click "Run Anyway")

         ✅ That's it! Everything installs automatically.
```

### Option B — Git Clone (Developers)

```bash
git clone https://github.com/mohammadquasif/ai-system-optimizer.git
cd ai-system-optimizer
INSTALL.bat
```

---

### What INSTALL.bat Does Step by Step

```
[1/7] Check Windows version          ← Confirms Windows 10/11 ✓
[2/7] Check Python                   ← Auto-installs Python 3.13 if missing
[3/7] Install Python packages         ← Installs all dependencies quietly
[4/7] Check Ollama                   ← Auto-installs Ollama if missing
[5/7] Check AI model                 ← Uses existing model if found, pulls if not
[6/7] Create shortcuts + startup     ← Desktop shortcut + Windows auto-start
[7/7] Launch app                     ← Opens the app immediately
```

> **No internet?** Place `OllamaSetup.exe` in the `installer\ollama\` folder  
> before running INSTALL.bat for a fully offline install.

---

## 🎮 How to Use

### ▶️ Starting the App

The app **starts automatically** with Windows.  
On startup it will say:

> *"Good Morning Quasif. Your system health is 94. AI assistant is ready."*

Then it displays the live dashboard.

### 💬 The Command Interface (Chips + Text + Voice)

Instead of complex menus, the app uses a **chat-style command area** at the bottom:

```
┌──────────────────────────────────────────────────────────────────┐
│ Quick Commands:                                                   │
│ [⚡ Optimize] [🧹 Clean] [📊 Status] [🧠 RAM Free] [🔗 DNS]     │
│ [❤️ Health]  [🚀 Startup] [🎙️ Voice On] [💡 Help]              │
├──────────────────────────────────────────────────────────────────┤
│  Type a command or question...                  [🎙️] [➤ Send]   │
└──────────────────────────────────────────────────────────────────┘
```

**Three ways to give commands:**

| Method | How |
| :--- | :--- |
| 🖱️ **Click a Chip** | Click any chip button above the input |
| ⌨️ **Type** | Write any command or question and press Enter |
| 🎙️ **Speak** | Click the microphone button and say your command |

**Example commands you can say or type:**
- *"Optimize my PC"* → runs full safe cleanup
- *"How is my RAM?"* → reports memory usage
- *"Clean browser cache"* → clears browser data
- *"Flush DNS"* → refreshes network connections
- *"What startup apps are running?"* → shows startup manager

---

## 🧹 Cleanup Features (Safe + Speed Boost)

### ✅ Default Safe Cleanup (Always On)

| Task | What It Does | RAM / Speed Benefit |
| :--- | :--- | :--- |
| 🗑️ **Windows Temp Files** | Deletes files in %TEMP% and C:\Windows\Temp | Frees disk space |
| 🖼️ **Thumbnail Cache** | Removes thumbcache_*.db from Explorer | Frees 100MB–1GB |
| 🎮 **GPU Shader Cache** | NVIDIA, AMD, Intel shader caches | Frees 200MB–2GB |
| 🌐 **Browser Cache** | Chrome, Edge, Brave, Opera, Firefox | Frees 100MB–5GB |
| 📋 **Temp Log Files** | .log, .tmp, .dmp in temp folders | Frees disk space |
| 🔗 **DNS Cache** | Flushes DNS → faster website loading | Network speed ⬆️ |
| 🐛 **Windows Error Reports** | Clears WER archive/queue | Frees disk space |
| 📋 **Clipboard** | Clears clipboard contents | Frees RAM |
| 📂 **Recent File Links** | Removes .lnk shortcuts in Recent | Frees disk space |
| 🧠 **RAM Trim** | Releases unused memory pages | **RAM freed ⬆️** |

### ⚙️ Optional Cleanup (User Selects)

| Task | What It Does | Note |
| :--- | :--- | :--- |
| ⚡ **Prefetch Cache** | Clears app launch prediction data | Windows rebuilds on next use |
| 🗑️ **Recycle Bin** | Empties recycle bin | Permanent |
| 📜 **Event Logs** | Clears Application/System event logs | Safe |
| 🔄 **Windows Update Cache** | Removes cached update files | Windows re-downloads if needed |

### ⚠️ Risky Options (Disabled by Default)

| Task | Risk | What Happens |
| :--- | :--- | :--- |
| Browser History | Medium | History is permanently deleted |
| Browser Cookies | High | **You will be logged out of websites** |

### ❌ What This App NEVER Touches

```
❌ Passwords            ❌ Bookmarks           ❌ Saved files
❌ Browser profiles     ❌ Login sessions       ❌ Extensions
❌ Autofill data        ❌ Personal documents   ❌ Downloads folder
```

---

## 💤 On-Demand Only — Zero Background RAM

This app is designed to **never waste your RAM**:

```
System Starts
    ↓
App Launches (auto-startup registry)
    ↓
Greets You by Voice
    ↓
Shows Live Dashboard
    ↓
You use it (or not)
    ↓
5 minutes of no interaction detected
    ↓
Status bar shows: "Idle — closing in 60s. Click anywhere to cancel."
    ↓
Voice says: "Closing now to free your memory. I'll be back when needed."
    ↓
App closes completely — 0 RAM used
    ↓
Next startup → repeats
(Or double-click icon anytime to relaunch on demand)
```

---

## 🎙️ Voice Commands Reference

| Say This | What Happens |
| :--- | :--- |
| *"Optimize"* | Runs full safe cleanup |
| *"Clean"* | Clears temp + browser cache |
| *"Status"* or *"How is my PC"* | Reports CPU/RAM/health score |
| *"RAM"* or *"Free memory"* | Runs RAM trim task |
| *"DNS"* | Flushes DNS cache |
| *"Health"* | Gives system health score |
| *"Startup"* | Opens startup apps manager |
| *"Help"* | Lists all available commands |
| *Any other question* | Sent to the local AI assistant |

---

## ⚙️ Requirements & Compatibility

| Item | Minimum | Recommended |
|:-----|:--------|:------------|
| OS | Windows 10 64-bit | Windows 11 |
| Python | 3.11 | 3.13 |
| RAM | 2 GB | 4+ GB |
| Disk | 1.5 GB free | 3+ GB |
| Internet | First setup only | Broadband for faster download |
| GPU | Not required | Any GPU |

---

## 🔒 Privacy & Security

- ✅ **100% Local AI** — Ollama runs on your machine
- ✅ **No Telemetry** — Zero data collection or tracking
- ✅ **Encrypted Settings** — API keys stored with AES-256
- ✅ **Open Source** — All code is fully auditable
- ✅ **No Admin Required** — Runs as a regular user

---

## 🛠️ Troubleshooting

| Problem | Solution |
|:--------|:---------|
| App does not open | Run `python app.py` in terminal to see the error |
| Ollama not detected | Restart app — it will retry setup automatically |
| Model download slow | Normal for 400MB–1GB. Keep app open, do not close. |
| Voice not working | Run: `pip install pipwin && pipwin install pyaudio` |
| No internet on first run | Place `OllamaSetup.exe` in `installer/ollama/` folder |
| App closes too quickly | Change idle time in Settings → Auto-close Minutes |

---

## 👤 About the Author

**Mohammad Quasif** is a technology strategist and DBA in Artificial Intelligence candidate. This project is part of his applied research into **Strategic AI Adoption** and **AI Engine Optimization (AIEO)**.

👉 **Full academic profile, certifications (IIT/AWS/Anthropic), and research portfolio:**  
[github.com/mohammadquasif](https://github.com/mohammadquasif)

---

## 🏷️ Tags

`ai-pc-optimizer` `windows-optimizer` `ollama` `local-ai` `voice-assistant`
`offline-ai` `on-demand-ai` `auto-cleanup` `ram-optimizer` `dns-flush`
`one-click-installer` `AI-Strategy` `Digital-Transformation` `Agentic-OS` `PhD-Research`

<div align="center">

⭐ **Star this repo if it helped you!** ⭐  
*Collaborators are welcome — help improve it for the community!*

</div>
