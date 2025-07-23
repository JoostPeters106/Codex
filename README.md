# Codex Darts Tournament Manager

This repository contains a simple web-based application for managing 8-player darts tournaments. All players start in a single group (Group A) before entering a single-elimination knockout bracket of seven players.

## Web Usage

Run the Flask server and open the page in your browser:

```bash
python app.py
```

Then navigate to `http://localhost:5000/` to use the tournament manager.

The main page allows an administrator to log in. Use the default credentials:

```
username: admin
password: password
```

Only an authenticated admin can create or modify tournaments.

## CLI Usage

A command-line implementation is also available. Run:

```bash
python tournament.py
```

Follow the prompts to enter player names and match scores. The script shuffles the players into Group A, calculates standings, and manages the knockout bracket.
