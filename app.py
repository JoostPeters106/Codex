from flask import Flask, render_template, request, redirect, url_for, session
from tournament import draw_group, schedule_round_robin
import json
import sqlite3
from datetime import datetime, timedelta

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "password"


DB_PATH = "tournaments.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        created_at TEXT,
        data TEXT
    )"""
    )
    conn.commit()
    conn.close()


init_db()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'replace-this-secret'
app.permanent_session_lifetime = timedelta(days=365)


@app.context_processor
def inject_tournament_name():
    name = None
    tid = session.get('current_tournament_id')
    if tid:
        conn = get_db()
        row = conn.execute('SELECT name FROM tournaments WHERE id=?', (tid,)).fetchone()
        conn.close()
        if row:
            name = row['name']
    else:
        title = session.get('tournament_title')
        if title:
            name = title
    return dict(current_tournament_name=name)


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session.permanent = True
        session['admin_logged_in'] = True
    return redirect(url_for('index'))


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/')
def index():
    players = session.get('players', [])
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, created_at, data FROM tournaments ORDER BY id DESC"
    ).fetchall()
    conn.close()
    tournaments = []
    for r in rows:
        data = json.loads(r["data"])
        tournaments.append(
            {
                "id": r["id"],
                "name": r["name"],
                "created_at": r["created_at"],
                "players": data.get("players", []),
            }
        )
    return render_template(
        'index.html', players=players, tournaments=tournaments
    )


@app.route('/add', methods=['POST'])
def add_player():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))
    name = request.form.get('player_name', '').strip()
    if name:
        players = session.get('players', [])
        players.append(name)
        session['players'] = players
    return redirect(url_for('index'))


@app.route('/remove/<int:index>', methods=['POST'])
def remove_player(index: int):
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))
    players = session.get('players', [])
    if 0 <= index < len(players):
        players.pop(index)
        session['players'] = players
    return redirect(url_for('index'))


@app.route('/set_title', methods=['POST'])
def set_title():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))
    title = request.form.get('tournament_title', '').strip()
    if title:
        session['tournament_title'] = title
    else:
        session.pop('tournament_title', None)
    return redirect(url_for('index'))


@app.route('/start', methods=['POST'])
def start_tournament():
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))
    players = session.get('players', [])
    if not players:
        return redirect(url_for('index'))
    group_a = draw_group(players.copy())
    schedule_a = [{
        'p1': m.p1,
        'p2': m.p2,
        'score1': None,
        'score2': None,
        'round': m.round,
    } for m in schedule_round_robin(group_a)]
    standings_a = [{'name': p, 'points': 0, 'gd': 0} for p in group_a]

    tournament_data = {
        'players': players,
        'group_a': group_a,
        'schedule_a': schedule_a,
        'standings_a': standings_a,
    }

    conn = get_db()
    name = session.pop('tournament_title', '').strip()
    if not name:
        name = f"Tournament {datetime.utcnow().isoformat(timespec='seconds')}"
    cur = conn.execute(
        "INSERT INTO tournaments (name, created_at, data) VALUES (?, ?, ?)",
        (name, datetime.utcnow().isoformat(timespec='seconds'), json.dumps(tournament_data)),
    )
    tid = cur.lastrowid
    conn.commit()
    conn.close()

    session['current_tournament_id'] = tid
    session.pop('players', None)
    return render_template('loading.html', t_id=tid)


def _find_standing(standings, name):
    for s in standings:
        if s['name'] == name:
            return s
    raise ValueError('player not found')


def _apply_result(match, standings):
    s1 = match['score1']
    s2 = match['score2']
    p1 = match['p1']
    p2 = match['p2']
    if s1 is None or s2 is None:
        return
    if s1 > s2:
        _find_standing(standings, p1)['points'] += 3
    elif s2 > s1:
        _find_standing(standings, p2)['points'] += 3
    else:
        _find_standing(standings, p1)['points'] += 1
        _find_standing(standings, p2)['points'] += 1
    _find_standing(standings, p1)['gd'] += s1 - s2
    _find_standing(standings, p2)['gd'] += s2 - s1

def _revert_result(match, standings):
    s1 = match['score1']
    s2 = match['score2']
    p1 = match['p1']
    p2 = match['p2']
    if s1 is None or s2 is None:
        return
    if s1 > s2:
        _find_standing(standings, p1)['points'] -= 3
    elif s2 > s1:
        _find_standing(standings, p2)['points'] -= 3
    else:
        _find_standing(standings, p1)['points'] -= 1
        _find_standing(standings, p2)['points'] -= 1
    _find_standing(standings, p1)['gd'] -= s1 - s2
    _find_standing(standings, p2)['gd'] -= s2 - s1


def _compute_knockout_bracket(sorted_standings):
    """Return knockout bracket pairs for top 7 players."""
    if len(sorted_standings) < 7:
        return None
    players = [s['name'] for s in sorted_standings[:7]]
    bye = players[0]
    others = players[1:]
    qfs = [
        {'p1': others[0], 'p2': others[5]},
        {'p1': others[1], 'p2': others[4]},
        {'p1': others[2], 'p2': others[3]},
    ]
    sfs = [
        {
            'p1': bye,
            'p2': f"Winner of {qfs[2]['p1']} vs {qfs[2]['p2']}"
        },
        {
            'p1': f"Winner of {qfs[0]['p1']} vs {qfs[0]['p2']}",
            'p2': f"Winner of {qfs[1]['p1']} vs {qfs[1]['p2']}"
        },
    ]
    final = {
        'p1': 'Winner of Semifinal 1',
        'p2': 'Winner of Semifinal 2'
    }
    return {'qfs': qfs, 'sfs': sfs, 'final': final}


@app.route('/tournament/<int:t_id>/record/<group>/<int:index>', methods=['POST'])
def record_score(t_id: int, group: str, index: int):
    if not session.get('admin_logged_in'):
        return redirect(url_for('tournament_view', t_id=t_id))
    if group != 'A':
        return redirect(url_for('tournament_view', t_id=t_id))

    conn = get_db()
    row = conn.execute("SELECT data FROM tournaments WHERE id=?", (t_id,)).fetchone()
    if row is None:
        conn.close()
        return redirect(url_for('index'))
    data = json.loads(row['data'])

    schedule = data.get('schedule_a')
    standings = data.get('standings_a')
    if schedule is None or standings is None or not (0 <= index < len(schedule)):
        conn.close()
        return redirect(url_for('tournament_view', t_id=t_id))

    match = schedule[index]
    _revert_result(match, standings)

    try:
        match['score1'] = int(request.form.get('score1'))
        match['score2'] = int(request.form.get('score2'))
    except (TypeError, ValueError):
        match['score1'] = match['score2'] = None
        conn.close()
        return redirect(url_for('tournament_view', t_id=t_id))

    _apply_result(match, standings)

    conn.execute(
        "UPDATE tournaments SET data=? WHERE id=?",
        (json.dumps(data), t_id),
    )
    conn.commit()
    conn.close()
    return redirect(url_for('tournament_view', t_id=t_id))


@app.route('/tournament')
def tournament_current():
    tid = session.get('current_tournament_id')
    if not tid:
        return redirect(url_for('index'))
    return redirect(url_for('tournament_view', t_id=tid))


@app.route('/tournament/<int:t_id>')
def tournament_view(t_id: int):
    conn = get_db()
    row = conn.execute('SELECT name, data FROM tournaments WHERE id=?', (t_id,)).fetchone()
    conn.close()
    if row is None:
        return redirect(url_for('index'))
    data = json.loads(row['data'])
    session['current_tournament_id'] = t_id
    standings_a = data.get('standings_a', [])
    standings_a = sorted(standings_a, key=lambda x: (-x['points'], -x['gd']))

    schedule_a = data.get('schedule_a', [])
    rounds = {}
    for m in schedule_a:
        rounds.setdefault(m.get('round', 1), []).append(m)
    schedule_by_round = [rounds[r] for r in sorted(rounds)]
    return render_template(
        'tournament.html',
        players=data.get('players', []),
        group_a=data.get('group_a', []),
        schedule_rounds=schedule_by_round,
        standings_a=standings_a,
        t_id=t_id,
    )


@app.route('/tournament/<int:t_id>/knockout')
def knockout_view(t_id: int):
    conn = get_db()
    row = conn.execute('SELECT name, data FROM tournaments WHERE id=?', (t_id,)).fetchone()
    conn.close()
    if row is None:
        return redirect(url_for('index'))
    data = json.loads(row['data'])
    session['current_tournament_id'] = t_id
    standings_a = data.get('standings_a', [])
    standings_a = sorted(standings_a, key=lambda x: (-x['points'], -x['gd']))
    bracket = _compute_knockout_bracket(standings_a)
    return render_template('knockout.html', bracket=bracket, t_id=t_id)


@app.route('/delete/<int:t_id>', methods=['POST'])
def delete_tournament(t_id: int):
    if not session.get('admin_logged_in'):
        return redirect(url_for('index'))
    conn = get_db()
    conn.execute('DELETE FROM tournaments WHERE id=?', (t_id,))
    conn.commit()
    conn.close()
    if session.get('current_tournament_id') == t_id:
        session.pop('current_tournament_id', None)
        session.pop('players', None)
    return redirect(url_for('index'))


@app.route('/reset', methods=['POST'])
def reset():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
