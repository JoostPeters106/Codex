# Codex Darts Tournament Manager

This repository contains a simple web-based application for managing 8-player darts tournaments. The app supports a group stage and a single-elimination knockout bracket of seven players.

## Web Usage

Run the Flask server and open the page in your browser:

```bash
python app.py
```

Then navigate to `http://localhost:5000/` to use the tournament manager.

## CLI Usage

A command-line implementation is also available. Run:

```bash
python tournament.py
```

Follow the prompts to enter player names and match scores. The script will randomize group assignments, calculate standings, and manage the knockout bracket.
