from flask import Flask, render_template, request, redirect, url_for, session

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

if __name__ == '__main__':
    app.run(debug=True)
