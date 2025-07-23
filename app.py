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


@app.context_processor
def inject_current_year():
    return {'current_year': datetime.utcnow().year}


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
    """Create a knockout bracket for 4-12 players based on standings."""
    seeds = [s['name'] for s in sorted_standings]
    n = len(seeds)
    if n < 4:
        return None

    bracket = {'size': n, 'seeds': seeds}

    # reduce players based on advancing rules
    if n == 5:
        seeds = seeds[:4]
    elif n == 6:
        seeds = seeds[:5]
    elif n == 8:
        seeds = seeds[:7]
    elif n == 9:
        seeds = seeds[:8]
    elif n == 10:
        seeds = seeds[:8]
    elif n == 11:
        seeds = seeds[:10]
    elif n >= 12:
        seeds = seeds[:12]

    m = len(seeds)

    playins = []
    qfs = []
    sfs = []

    if m <= 4:
        # direct semifinals
        sfs = [
            {'p1': seeds[0], 'p2': seeds[3], 'score1': None, 'score2': None},
            {'p1': seeds[1], 'p2': seeds[2], 'score1': None, 'score2': None},
        ]
    elif m == 5:
        playins = [
            {'p1': seeds[3], 'p2': seeds[4], 'score1': None, 'score2': None}
        ]
        sfs = [
            {
                'p1': seeds[0],
                'p2': f"Winner of {seeds[3]} vs {seeds[4]}",
                'score1': None,
                'score2': None,
            },
            {'p1': seeds[1], 'p2': seeds[2], 'score1': None, 'score2': None},
        ]
    elif m == 7:
        qfs = [
            {'p1': seeds[1], 'p2': seeds[6], 'score1': None, 'score2': None},
            {'p1': seeds[2], 'p2': seeds[5], 'score1': None, 'score2': None},
            {'p1': seeds[3], 'p2': seeds[4], 'score1': None, 'score2': None},
        ]
        sfs = [
            {'p1': seeds[0], 'p2': None, 'score1': None, 'score2': None},
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
        ]
    elif m == 8:
        qfs = [
            {'p1': seeds[0], 'p2': seeds[7], 'score1': None, 'score2': None},
            {'p1': seeds[1], 'p2': seeds[6], 'score1': None, 'score2': None},
            {'p1': seeds[2], 'p2': seeds[5], 'score1': None, 'score2': None},
            {'p1': seeds[3], 'p2': seeds[4], 'score1': None, 'score2': None},
        ]
        sfs = [
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
        ]
    elif m == 10:
        playins = [
            {'p1': seeds[6], 'p2': seeds[9], 'score1': None, 'score2': None},
            {'p1': seeds[7], 'p2': seeds[8], 'score1': None, 'score2': None},
        ]
        qfs = [
            {'p1': seeds[0], 'p2': f"Winner of {seeds[7]} vs {seeds[8]}", 'score1': None, 'score2': None},
            {'p1': seeds[1], 'p2': f"Winner of {seeds[6]} vs {seeds[9]}", 'score1': None, 'score2': None},
            {'p1': seeds[2], 'p2': seeds[5], 'score1': None, 'score2': None},
            {'p1': seeds[3], 'p2': seeds[4], 'score1': None, 'score2': None},
        ]
        sfs = [
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
        ]
    elif m == 12:
        playins = [
            {'p1': seeds[5], 'p2': seeds[10], 'score1': None, 'score2': None},
            {'p1': seeds[6], 'p2': seeds[9], 'score1': None, 'score2': None},
            {'p1': seeds[7], 'p2': seeds[8], 'score1': None, 'score2': None},
            {'p1': seeds[11], 'p2': seeds[4], 'score1': None, 'score2': None},
        ]
        qfs = [
            {'p1': seeds[0], 'p2': f"Winner of {seeds[7]} vs {seeds[8]}", 'score1': None, 'score2': None},
            {'p1': seeds[1], 'p2': f"Winner of {seeds[6]} vs {seeds[9]}", 'score1': None, 'score2': None},
            {'p1': seeds[2], 'p2': f"Winner of {seeds[5]} vs {seeds[10]}", 'score1': None, 'score2': None},
            {'p1': seeds[3], 'p2': f"Winner of {seeds[11]} vs {seeds[4]}", 'score1': None, 'score2': None},
        ]
        sfs = [
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
            {'p1': None, 'p2': None, 'score1': None, 'score2': None},
        ]

    final = {'p1': 'Winner of Semifinal 1', 'p2': 'Winner of Semifinal 2', 'score1': None, 'score2': None}

    if playins:
        bracket['playins'] = playins
    if qfs:
        bracket['qfs'] = qfs
    if sfs:
        bracket['sfs'] = sfs
    bracket['final'] = final
    return bracket


def _update_knockout_progress(bracket):
    """Fill next round matchups based on completed scores."""
    if bracket is None:
        return

    size = bracket.get('size', 0)

    playin_winners = []
    for m in bracket.get('playins', []):
        s1, s2 = m.get('score1'), m.get('score2')
        if s1 is not None and s2 is not None:
            playin_winners.append(m['p1'] if s1 >= s2 else m['p2'])
        else:
            playin_winners.append(None)

    if size == 6 and playin_winners:
        if playin_winners[0]:
            bracket['sfs'][0]['p2'] = playin_winners[0]

    if size == 11 and len(playin_winners) == 2:
        if playin_winners[1]:
            bracket['qfs'][0]['p2'] = playin_winners[1]
        if playin_winners[0]:
            bracket['qfs'][1]['p2'] = playin_winners[0]

    if size >= 12 and len(playin_winners) == 4:
        if playin_winners[2]:
            bracket['qfs'][0]['p2'] = playin_winners[2]
        if playin_winners[1]:
            bracket['qfs'][1]['p2'] = playin_winners[1]
        if playin_winners[0]:
            bracket['qfs'][2]['p2'] = playin_winners[0]
        if playin_winners[3]:
            bracket['qfs'][3]['p2'] = playin_winners[3]

    winners_qf = []
    for m in bracket.get('qfs', []):
        s1, s2 = m.get('score1'), m.get('score2')
        if s1 is not None and s2 is not None:
            winners_qf.append(m['p1'] if s1 >= s2 else m['p2'])
        else:
            winners_qf.append(None)

    if size in (7, 8) and len(winners_qf) == 3 and all(winners_qf):
        seed_map = {p: i for i, p in enumerate(bracket['seeds'][:7])}
        winners_sorted = sorted(winners_qf, key=lambda p: seed_map.get(p, 100))
        lowest = winners_sorted[-1]
        others = [w for w in winners_sorted if w != lowest]
        bracket['sfs'][0]['p2'] = lowest
        bracket['sfs'][1]['p1'] = others[0]
        bracket['sfs'][1]['p2'] = others[1]
    elif size >= 8 and len(winners_qf) >= 4:
        if winners_qf[0] and winners_qf[-1]:
            bracket['sfs'][0]['p1'] = winners_qf[0]
            bracket['sfs'][0]['p2'] = winners_qf[-1]
        if winners_qf[1] and winners_qf[2]:
            bracket['sfs'][1]['p1'] = winners_qf[1]
            bracket['sfs'][1]['p2'] = winners_qf[2]

    winners_sf = []
    for m in bracket.get('sfs', []):
        s1, s2 = m.get('score1'), m.get('score2')
        p1, p2 = m.get('p1'), m.get('p2')
        if p1 and p2 and s1 is not None and s2 is not None:
            winners_sf.append(p1 if s1 >= s2 else p2)

    if len(winners_sf) == 2 and 'final' in bracket:
        bracket['final']['p1'] = winners_sf[0]
        bracket['final']['p2'] = winners_sf[1]


def _players_known(match):
    """Return True if both players have been decided."""
    p1 = match.get('p1')
    p2 = match.get('p2')
    if not p1 or not p2:
        return False
    return not str(p1).startswith('Winner') and not str(p2).startswith('Winner')


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


@app.route('/tournament/<int:t_id>/record_knockout/<stage>/<int:index>', methods=['POST'])
def record_knockout_score(t_id: int, stage: str, index: int):
    if not session.get('admin_logged_in'):
        return redirect(url_for('knockout_view', t_id=t_id))

    conn = get_db()
    row = conn.execute("SELECT data FROM tournaments WHERE id=?", (t_id,)).fetchone()
    if row is None:
        conn.close()
        return redirect(url_for('index'))
    data = json.loads(row['data'])

    bracket = data.get('knockout')
    if bracket is None:
        standings = data.get('standings_a', [])
        standings = sorted(standings, key=lambda x: (-x['points'], -x['gd']))
        bracket = _compute_knockout_bracket(standings)
        data['knockout'] = bracket

    if stage == 'final':
        match = bracket['final']
    elif stage in ('playins', 'qfs', 'sfs'):
        matches = bracket.get(stage)
        if matches is None or not (0 <= index < len(matches)):
            conn.close()
            return redirect(url_for('knockout_view', t_id=t_id))
        match = matches[index]
    else:
        conn.close()
        return redirect(url_for('knockout_view', t_id=t_id))

    if stage in ('sfs', 'final') and not _players_known(match):
        conn.close()
        return redirect(url_for('knockout_view', t_id=t_id))

    try:
        match['score1'] = int(request.form.get('score1'))
        match['score2'] = int(request.form.get('score2'))
    except (TypeError, ValueError):
        match['score1'] = match['score2'] = None
        conn.close()
        return redirect(url_for('knockout_view', t_id=t_id))

    _update_knockout_progress(bracket)

    conn.execute("UPDATE tournaments SET data=? WHERE id=?", (json.dumps(data), t_id))
    conn.commit()
    conn.close()
    return redirect(url_for('knockout_view', t_id=t_id))


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

    bracket = data.get('knockout')
    if bracket is None:
        bracket = _compute_knockout_bracket(standings_a)
        data['knockout'] = bracket
        conn = get_db()
        conn.execute("UPDATE tournaments SET data=? WHERE id=?", (json.dumps(data), t_id))
        conn.commit()
        conn.close()
    else:
        _update_knockout_progress(bracket)
        conn = get_db()
        conn.execute("UPDATE tournaments SET data=? WHERE id=?", (json.dumps(data), t_id))
        conn.commit()
        conn.close()

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
