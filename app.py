from flask import Flask, render_template, request, redirect, url_for, session
from tournament import draw_groups, schedule_round_robin

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'replace-this-secret'

@app.route('/')
def index():
    players = session.get('players', [])
    return render_template('index.html', players=players)


@app.route('/add', methods=['POST'])
def add_player():
    name = request.form.get('player_name', '').strip()
    if name:
        players = session.get('players', [])
        players.append(name)
        session['players'] = players
    return redirect(url_for('index'))


@app.route('/remove/<int:index>', methods=['POST'])
def remove_player(index: int):
    players = session.get('players', [])
    if 0 <= index < len(players):
        players.pop(index)
        session['players'] = players
    return redirect(url_for('index'))


@app.route('/start', methods=['POST'])
def start_tournament():
    players = session.get('players', [])
    if not players:
        return redirect(url_for('index'))
    group_a, group_b = draw_groups(players.copy())
    schedule_a = [{
        'p1': m.p1,
        'p2': m.p2,
        'score1': None,
        'score2': None,
    } for m in schedule_round_robin(group_a)]
    schedule_b = [{
        'p1': m.p1,
        'p2': m.p2,
        'score1': None,
        'score2': None,
    } for m in schedule_round_robin(group_b)]
    standings_a = [{'name': p, 'points': 0, 'gd': 0} for p in group_a]
    standings_b = [{'name': p, 'points': 0, 'gd': 0} for p in group_b]
    session['tournament'] = {
        'group_a': group_a,
        'group_b': group_b,
        'schedule_a': schedule_a,
        'schedule_b': schedule_b,
        'standings_a': standings_a,
        'standings_b': standings_b,
    }
    return redirect(url_for('tournament_view'))


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


@app.route('/record/<group>/<int:index>', methods=['POST'])
def record_score(group: str, index: int):
    t = session.get('tournament')
    if not t:
        return redirect(url_for('index'))

    schedule_key = 'schedule_a' if group == 'A' else 'schedule_b'
    standings_key = 'standings_a' if group == 'A' else 'standings_b'

    schedule = t.get(schedule_key)
    standings = t.get(standings_key)
    if schedule is None or standings is None:
        return redirect(url_for('tournament_view'))
    if not (0 <= index < len(schedule)):
        return redirect(url_for('tournament_view'))

    match = schedule[index]
    _revert_result(match, standings)

    try:
        match['score1'] = int(request.form.get('score1'))
        match['score2'] = int(request.form.get('score2'))
    except (TypeError, ValueError):
        match['score1'] = match['score2'] = None
        return redirect(url_for('tournament_view'))

    _apply_result(match, standings)
    session['tournament'] = t
    return redirect(url_for('tournament_view'))


@app.route('/tournament')
def tournament_view():
    t = session.get('tournament')
    if not t:
        return redirect(url_for('index'))
    players = session.get('players', [])
    return render_template('tournament.html', players=players, **t)


@app.route('/reset', methods=['POST'])
def reset():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
