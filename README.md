# MazeSnek

MazeSnek is a command-line MoltMaze solver for Ubuntu Linux. It is meant to be installed on a small Linux box or Ubuntu VM and start solving mazes immediately with a valid MoltMaze API key.

The main entry point is:

```bash
mazesnek <apikey>
```

By default, MazeSnek talks to `https://moltmaze.com`, resumes the active run if one exists, or starts a run if it does not, then continuously:

1. fetches fresh state,
2. finds a path to the goal,
3. chooses the next direction,
4. solves the equation bound to that direction,
5. submits the numeric answer,
6. repeats until the run ends or you stop it.

This matches how MoltMaze describes its bot flow and API surface.

## Features

- `mazesnek <apikey>` simple CLI
- starts or resumes automatically
- BFS pathfinding to the goal
- safe arithmetic solver for action equations
- readable terminal output
- configurable base URL and poll interval
- packaged as a normal Python project with a console script

## MoltMaze endpoints used

MoltMaze documents these main endpoints:

- `api/start_run.php`
- `api/current_run.php`
- `api/get_state.php`
- `api/submit_move.php`

It also notes that action mappings can change every turn, so bots should fetch fresh state often.

## Ubuntu VM setup

These steps assume Ubuntu 24.04 LTS in VirtualBox, but they are also fine on a normal Ubuntu machine.

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Clone the repo

```bash
git clone https://github.com/YOURNAME/MazeSnek.git
cd MazeSnek
```

### 3. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install MazeSnek

For development:

```bash
pip install -e .
```

Or as a normal local install:

```bash
pip install .
```

### 5. Run it

```bash
mazesnek YOUR_API_KEY
```

## Usage

### Simplest form

```bash
mazesnek YOUR_API_KEY
```

### Custom poll interval

```bash
mazesnek YOUR_API_KEY --poll 0.15
```

### Custom server

```bash
mazesnek YOUR_API_KEY --base-url https://moltmaze.com
```

### Start a new run instead of resuming

```bash
mazesnek YOUR_API_KEY --force-new-run
```

### Show raw state parsing details

```bash
mazesnek YOUR_API_KEY --debug
```

## Getting an API key

MoltMaze says you create a bot profile and receive the API key once, and that key is then used for starting runs, reading state, and submitting moves.

Example registration call from MoltMaze:

```bash
curl -X POST https://moltmaze.com/api/register_bot.php \
  -H "Content-Type: application/json" \
  -d '{"name":"my-bot-name"}'
```

## How MazeSnek works

MazeSnek expects the MoltMaze state endpoint to include, in some form:

- current maze/grid
- current position
- goal position
- current action equations
- run identifier

The homepage explains that the state payload includes run status, current position, goal position, maze size, score, current action equations, and maze data.

The parser in this package is intentionally tolerant and tries several common key names so it can survive small API naming changes.

## Example workflow

```bash
mazesnek YOUR_API_KEY --poll 0.10
```

Typical loop:

- call `start_run.php`
- call `get_state.php`
- pathfind to the goal
- solve the equation for the chosen move
- call `submit_move.php`
- repeat

## Running as a persistent service on Ubuntu

Create a user service:

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/mazesnek.service
```

Paste:

```ini
[Unit]
Description=MazeSnek MoltMaze solver
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/MazeSnek
ExecStart=%h/MazeSnek/.venv/bin/mazesnek YOUR_API_KEY --poll 0.15
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```

Then enable it:

```bash
systemctl --user daemon-reload
systemctl --user enable --now mazesnek.service
loginctl enable-linger "$USER"
```

Watch logs:

```bash
journalctl --user -u mazesnek.service -f
```

## Project layout

```text
MazeSnek/
├── README.md
├── pyproject.toml
└── mazesnek/
    ├── __init__.py
    ├── cli.py
    ├── client.py
    ├── pathfinding.py
    ├── solver.py
    └── state.py
```

## Notes

- MazeSnek is designed for legitimate play against MoltMaze using the documented bot API.
- The parser is flexible, but if the live API shape changes substantially you may need to adjust `mazesnek/state.py`.
- Very stale state can cause wrong submissions because MoltMaze rebinds equations every turn. That behavior is documented on the homepage.
