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
    schedule_a = [(m.p1, m.p2) for m in schedule_round_robin(group_a)]
    schedule_b = [(m.p1, m.p2) for m in schedule_round_robin(group_b)]
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


@app.route('/tournament')
def tournament_view():
    t = session.get('tournament')
    if not t:
        return redirect(url_for('index'))
    players = session.get('players', [])
    return render_template('tournament.html', players=players, **t)

if __name__ == '__main__':
    app.run(debug=True)
