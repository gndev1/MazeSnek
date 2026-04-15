# MazeSnek

MazeSnek is a command-line bot for **MoltMaze** and a clean open-source reference implementation for developers who want to study, fork, and build their own bots.

It is designed to be:

- easy to install
- easy to run
- easy to read
- easy to modify

For a full walkthrough, see **GETTING_STARTED.md**

---

## Features

- command-line MoltMaze bot
- automatic run start/resume
- BFS-based pathfinding
- deterministic equation solver
- structured debug output
- modular architecture for extension

---

## Requirements

- Python 3.10+
- pip
- venv
- git

---

# Install on Linux / Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git

git clone https://github.com/YOURNAME/MazeSnek.git
cd MazeSnek

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .
```

---

# Install on Windows

⚠️ Always run commands from the project root (the folder containing `pyproject.toml`)

## Create virtual environment

```bat
py -m venv .venv
```

## Activate

### Command Prompt (cmd.exe)

```bat
.venv\Scripts\activate
```

### PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

## Install

```bat
pip install --upgrade pip
pip install -e .
```

---

# Running MazeSnek

```bash
mazesnek YOUR_API_KEY
```

If the command is not recognized:

```bash
python -m mazesnek.cli YOUR_API_KEY
```

---

# Debug Mode

```bash
mazesnek YOUR_API_KEY --debug
```

Shows:

- run / level / turn
- position / goal
- chosen direction
- equation text
- computed answer
- server response

---

# Common Arguments

## Custom server

```bash
mazesnek YOUR_API_KEY --base-url https://moltmaze.com
```

## Poll rate

```bash
mazesnek YOUR_API_KEY --poll-seconds 0.15
```

## Force new run

```bash
mazesnek YOUR_API_KEY --force-new-run
```

---

# Getting an API Key

```bash
curl -X POST https://moltmaze.com/api/register_bot.php \
  -H "Content-Type: application/json" \
  -d '{"name":"my-bot"}'
```

---

# Common Issues (Windows)

## 1. 'mazesnek not recognized'

Use:

```bat
python -m mazesnek.cli YOUR_API_KEY
```

---

## 2. After reboot

```bat
cd path\to\MazeSnek
.venv\Scripts\activate
```

---

## 3. Broken environment

```bat
rmdir /s /q .venv
py -m venv .venv
.venv\Scripts\activate
pip install -e .
```

---

## 4. Running from wrong folder

❌ Wrong:
```
MazeSnek\mazesnek\
```

✅ Correct:
```
MazeSnek\
```

---

# Project Layout

```
MazeSnek/
├── README.md
├── GETTING_STARTED.md
├── pyproject.toml
└── mazesnek/
    ├── cli.py
    ├── client.py
    ├── solver.py
    ├── pathfinding.py
    └── state.py
```

---

# Development Notes

MazeSnek is intentionally simple and designed to be extended.

Key areas to improve:

- smarter pathfinding
- heuristic weighting
- equation solving optimizations
- adaptive retry logic

---

# Summary

MazeSnek is a working reference bot.

If something breaks:
- it is usually environment setup
- or server-side challenge behavior

Use debug mode to inspect behavior and iterate quickly.
