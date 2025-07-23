# Codex Darts Tournament Manager

This repository contains a simple web-based application for managing darts tournaments. Any number of players from four up to twelve can be entered. All players start in a single group (Group A) before entering a knockout bracket seeded by the group results.

## Web Usage

Run the Node.js server and open the page in your browser:

```bash
npm install
node server.js
```

Then navigate to `http://localhost:5000/` to use the tournament manager.

The main page allows an administrator to log in. Use the default credentials:

```
username: admin
password: password
```

Only an authenticated admin can create or modify tournaments.

The old Python CLI has been removed in favour of the JavaScript implementation.
