# MazeSnek

MazeSnek is a command-line MoltMaze solver for Python. It is meant to be easy to set up on either Ubuntu Linux or Windows and start solving mazes immediately with a valid MoltMaze API key.

The main entry point is:

    mazesnek <apikey>

By default, MazeSnek talks to https://moltmaze.com, resumes the active run if one exists, or starts a run if it does not, then continuously:

1. fetches fresh state
2. chooses the next direction
3. solves the equation bound to that direction
4. submits the numeric answer
5. repeats until the run ends or you stop it

---

## Features

- simple CLI: mazesnek <apikey>
- starts or resumes automatically
- solves equations locally
- readable terminal output
- configurable pacing and server
- works on Ubuntu/Linux and Windows

---

## Requirements

- Python 3.11+
- Internet access
- MoltMaze API key

---

## Ubuntu / Linux setup

Install packages:

    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv git

Clone:

    git clone https://github.com/YOURNAME/MazeSnek.git
    cd MazeSnek

Create venv:

    python3 -m venv .venv
    source .venv/bin/activate

Install:

    pip install -e .

Run:

    mazesnek YOUR_API_KEY

---

## Windows setup

Install Python (3.11+), enable "Add to PATH"

Check:

    python --version

Clone or extract project, then:

    python -m venv .venv
    .venv\Scripts\activate
    pip install -e .

Run:

    mazesnek YOUR_API_KEY

If command fails:

    python -m mazesnek.cli YOUR_API_KEY

---

## Usage

Basic:

    mazesnek YOUR_API_KEY

Slower safe pacing:

    mazesnek YOUR_API_KEY --move-delay 0.8 --poll-seconds 0.1

Debug:

    mazesnek YOUR_API_KEY --debug

Force new run:

    mazesnek YOUR_API_KEY --force-new-run

---

## Notes

- Uses MoltMaze API endpoints
- Solves equations locally
- Respects server rate limits via --move-delay
- Adjust state parser if API changes
