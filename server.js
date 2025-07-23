const express = require('express');
const session = require('express-session');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const nunjucks = require('nunjucks');
const {
  drawGroup,
  scheduleRoundRobin,
  _applyResult,
  _revertResult,
  _playersKnown,
  _computeKnockoutBracket,
  _updateKnockoutProgress,
} = require('./tournament');

const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'password';
const DB_PATH = 'tournaments.db';

const app = express();
app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(path.join(__dirname, 'static')));

const nunjucksEnv = nunjucks.configure('templates', { autoescape: true, express: app });
nunjucksEnv.addGlobal('url_for', url_for);

app.use(
  session({
    secret: 'replace-this-secret',
    resave: false,
    saveUninitialized: true,
  })
);

// initialize database
(function initDb() {
  const db = new sqlite3.Database(DB_PATH);
  db.run(
    `CREATE TABLE IF NOT EXISTS tournaments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      created_at TEXT,
      data TEXT
    )`
  );
  db.close();
})();

function getDb() {
  return new sqlite3.Database(DB_PATH);
}

// url_for helper similar to Flask
const routes = {
  index: '/',
  login: '/login',
  logout: '/logout',
  add_player: '/add',
  remove_player: (p) => `/remove/${p.index}`,
  set_title: '/set_title',
  start_tournament: '/start',
  tournament_view: (p) => `/tournament/${p.t_id}`,
  knockout_view: (p) => `/tournament/${p.t_id}/knockout`,
  record_score: (p) =>
    `/tournament/${p.t_id}/record/${p.group}/${p.index}`,
  record_knockout_score: (p) =>
    `/tournament/${p.t_id}/record_knockout/${p.stage}/${p.index}`,
  delete_tournament: (p) => `/delete/${p.t_id}`,
  reset: '/reset',
  tournament_current: '/tournament',
  static: (p) => `/static/${p.filename}`,
};

function url_for(name, params = {}) {
  const route = routes[name];
  if (!route) return '#';
  return typeof route === 'function' ? route(params) : route;
}


// middleware to inject globals similar to Flask context processors
app.use((req, res, next) => {
  res.locals.current_year = new Date().getFullYear();
  const tid = req.session.current_tournament_id;
  if (tid) {
    const db = getDb();
    db.get('SELECT name FROM tournaments WHERE id=?', [tid], (err, row) => {
      if (!err && row) {
        res.locals.current_tournament_name = row.name;
      } else if (req.session.tournament_title) {
        res.locals.current_tournament_name = req.session.tournament_title;
      }
      db.close();
      next();
    });
  } else {
    if (req.session.tournament_title) {
      res.locals.current_tournament_name = req.session.tournament_title;
    }
    next();
  }
});

app.get('/', (req, res) => {
  const db = getDb();
  const per_page = 3;
  const page = parseInt(req.query.page || '1', 10);
  db.all('SELECT COUNT(*) as c FROM tournaments', [], (err, rows) => {
    const total = rows[0].c;
    db.all(
      'SELECT id, name, created_at, data FROM tournaments ORDER BY id DESC LIMIT ? OFFSET ?',
      [per_page, (page - 1) * per_page],
      (err2, dataRows) => {
        db.close();
        const tournaments = dataRows.map((r) => {
          const data = JSON.parse(r.data);
          return {
            id: r.id,
            name: r.name,
            created_at: r.created_at,
            players: data.players || [],
          };
        });
        res.render('index.html', {
          players: req.session.players || [],
          tournaments,
          page,
          has_next: page * per_page < total,
          has_prev: page > 1,
          session: req.session,
        });
      }
    );
  });
});

app.post('/login', (req, res) => {
  const { username, password } = req.body;
  if (username === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
    req.session.admin_logged_in = true;
  }
  res.redirect('/');
});

app.post('/logout', (req, res) => {
  req.session.admin_logged_in = false;
  res.redirect('/');
});

app.post('/add', (req, res) => {
  if (!req.session.admin_logged_in) return res.redirect('/');
  const name = (req.body.player_name || '').trim();
  if (name) {
    const players = req.session.players || [];
    players.push(name);
    req.session.players = players;
  }
  res.redirect('/');
});

app.post('/remove/:index', (req, res) => {
  if (!req.session.admin_logged_in) return res.redirect('/');
  const idx = parseInt(req.params.index, 10);
  const players = req.session.players || [];
  if (idx >= 0 && idx < players.length) {
    players.splice(idx, 1);
    req.session.players = players;
  }
  res.redirect('/');
});

app.post('/set_title', (req, res) => {
  if (!req.session.admin_logged_in) return res.redirect('/');
  const title = (req.body.tournament_title || '').trim();
  if (title) req.session.tournament_title = title;
  else delete req.session.tournament_title;
  res.redirect('/');
});

app.post('/start', (req, res) => {
  if (!req.session.admin_logged_in) return res.redirect('/');
  const players = req.session.players || [];
  if (players.length === 0) return res.redirect('/');
  const group_a = drawGroup(players.slice());
  const schedule_a = scheduleRoundRobin(group_a).map((m, idx) => ({
    p1: m.p1,
    p2: m.p2,
    score1: null,
    score2: null,
    round: m.round,
    idx,
  }));
  const standings_a = group_a.map((p) => ({ name: p, points: 0, gd: 0 }));
  const data = {
    players,
    group_a,
    schedule_a,
    standings_a,
  };
  const db = getDb();
  const name = (req.session.tournament_title || '').trim() || `Tournament ${new Date().toISOString().slice(0,19)}`;
  db.run(
    'INSERT INTO tournaments (name, created_at, data) VALUES (?, ?, ?)',
    [name, new Date().toISOString().slice(0,19), JSON.stringify(data)],
    function (err) {
      const tid = this.lastID;
      db.close();
      req.session.current_tournament_id = tid;
      delete req.session.players;
      res.render('loading.html', { t_id: tid, session: req.session });
    }
  );
});

app.get('/tournament', (req, res) => {
  const tid = req.session.current_tournament_id;
  if (!tid) return res.redirect('/');
  res.redirect(`/tournament/${tid}`);
});

app.get('/tournament/:t_id', (req, res) => {
  const t_id = parseInt(req.params.t_id, 10);
  const db = getDb();
  db.get('SELECT name, data FROM tournaments WHERE id=?', [t_id], (err, row) => {
    if (!row) {
      db.close();
      return res.redirect('/');
    }
    const data = JSON.parse(row.data);
    req.session.current_tournament_id = t_id;
    const standings_a = data.standings_a || [];
    standings_a.sort((a, b) => b.points - a.points || b.gd - a.gd);
    const rounds = {};
    for (const m of data.schedule_a || []) {
      rounds[m.round] = rounds[m.round] || [];
      rounds[m.round].push(m);
    }
    const schedule_rounds = Object.keys(rounds)
      .sort((a, b) => a - b)
      .map((r) => rounds[r]);
    db.close();
    res.render('tournament.html', {
      players: data.players || [],
      group_a: data.group_a || [],
      schedule_rounds,
      standings_a,
      t_id,
      session: req.session,
    });
  });
});

app.post('/tournament/:t_id/record/:group/:index', (req, res) => {
  const { t_id, group, index } = req.params;
  if (!req.session.admin_logged_in) return res.redirect(`/tournament/${t_id}`);
  if (group !== 'A') return res.redirect(`/tournament/${t_id}`);
  const idx = parseInt(index, 10);
  const db = getDb();
  db.get('SELECT data FROM tournaments WHERE id=?', [t_id], (err, row) => {
    if (!row) {
      db.close();
      return res.redirect('/');
    }
    const data = JSON.parse(row.data);
    const schedule = data.schedule_a || [];
    const standings = data.standings_a || [];
    if (idx < 0 || idx >= schedule.length) {
      db.close();
      return res.redirect(`/tournament/${t_id}`);
    }
    const match = schedule[idx];
    _revertResult(match, standings);
    const s1 = parseInt(req.body.score1, 10);
    const s2 = parseInt(req.body.score2, 10);
    if (!isNaN(s1) && !isNaN(s2)) {
      match.score1 = s1;
      match.score2 = s2;
    } else {
      match.score1 = match.score2 = null;
      db.close();
      return res.redirect(`/tournament/${t_id}`);
    }
    _applyResult(match, standings);
    db.run(
      'UPDATE tournaments SET data=? WHERE id=?',
      [JSON.stringify(data), t_id],
      () => {
        db.close();
        res.redirect(`/tournament/${t_id}`);
      }
    );
  });
});

app.get('/tournament/:t_id/knockout', (req, res) => {
  const t_id = parseInt(req.params.t_id, 10);
  const db = getDb();
  db.get('SELECT name, data FROM tournaments WHERE id=?', [t_id], (err, row) => {
    if (!row) {
      db.close();
      return res.redirect('/');
    }
    const data = JSON.parse(row.data);
    req.session.current_tournament_id = t_id;
    const standings_a = data.standings_a || [];
    standings_a.sort((a, b) => b.points - a.points || b.gd - a.gd);
    let bracket = data.knockout;
    if (!bracket) {
      bracket = _computeKnockoutBracket(standings_a);
      data.knockout = bracket;
      db.run(
        'UPDATE tournaments SET data=? WHERE id=?',
        [JSON.stringify(data), t_id],
        () => db.close()
      );
    } else {
      _updateKnockoutProgress(bracket);
      db.run(
        'UPDATE tournaments SET data=? WHERE id=?',
        [JSON.stringify(data), t_id],
        () => db.close()
      );
    }
    res.render('knockout.html', { bracket, t_id, session: req.session });
  });
});

app.post('/tournament/:t_id/record_knockout/:stage/:index', (req, res) => {
  const { t_id, stage, index } = req.params;
  if (!req.session.admin_logged_in) return res.redirect(`/tournament/${t_id}/knockout`);
  const idx = parseInt(index, 10);
  const db = getDb();
  db.get('SELECT data FROM tournaments WHERE id=?', [t_id], (err, row) => {
    if (!row) {
      db.close();
      return res.redirect('/');
    }
    const data = JSON.parse(row.data);
    let bracket = data.knockout;
    if (!bracket) {
      const standings = (data.standings_a || []).slice().sort((a,b)=> b.points - a.points || b.gd - a.gd);
      bracket = _computeKnockoutBracket(standings);
      data.knockout = bracket;
    }
    let match;
    if (stage === 'final') {
      match = bracket.final;
    } else if (['playins','qfs','sfs'].includes(stage)) {
      const matches = bracket[stage] || [];
      if (idx < 0 || idx >= matches.length) {
        db.close();
        return res.redirect(`/tournament/${t_id}/knockout`);
      }
      match = matches[idx];
    } else {
      db.close();
      return res.redirect(`/tournament/${t_id}/knockout`);
    }
    if (['sfs','final'].includes(stage) && !_playersKnown(match)) {
      db.close();
      return res.redirect(`/tournament/${t_id}/knockout`);
    }
    const s1 = parseInt(req.body.score1, 10);
    const s2 = parseInt(req.body.score2, 10);
    if (isNaN(s1) || isNaN(s2)) {
      match.score1 = match.score2 = null;
      db.close();
      return res.redirect(`/tournament/${t_id}/knockout`);
    }
    match.score1 = s1;
    match.score2 = s2;
    _updateKnockoutProgress(bracket);
    db.run(
      'UPDATE tournaments SET data=? WHERE id=?',
      [JSON.stringify(data), t_id],
      () => {
        db.close();
        res.redirect(`/tournament/${t_id}/knockout`);
      }
    );
  });
});

app.post('/delete/:t_id', (req, res) => {
  if (!req.session.admin_logged_in) return res.redirect('/');
  const t_id = parseInt(req.params.t_id, 10);
  const db = getDb();
  db.run('DELETE FROM tournaments WHERE id=?', [t_id], () => {
    db.close();
    if (req.session.current_tournament_id === t_id) {
      delete req.session.current_tournament_id;
      delete req.session.players;
    }
    res.redirect('/');
  });
});

app.post('/reset', (req, res) => {
  req.session.regenerate(() => {
    res.redirect('/');
  });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

// keep the Node.js process alive even if no connections are open
setInterval(() => {}, 1000);
