// Tournament utility functions ported from Python to JavaScript

function drawGroup(players) {
  // Randomly shuffle players into a single group
  players = players.slice();
  for (let i = players.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [players[i], players[j]] = [players[j], players[i]];
  }
  return players;
}

function scheduleRoundRobin(players) {
  // Create a round-robin schedule returning matches with round numbers
  players = players.slice();
  if (players.length % 2 === 1) {
    players.push(null);
  }
  const n = players.length;
  const rounds = [];
  for (let r = 0; r < n - 1; r++) {
    for (let i = 0; i < n / 2; i++) {
      const p1 = players[i];
      const p2 = players[n - 1 - i];
      if (p1 && p2) {
        rounds.push({ p1, p2, score1: null, score2: null, round: r + 1 });
      }
    }
    players = [players[0]].concat(players.slice(-1), players.slice(1, -1));
  }
  return rounds;
}

function _findStanding(standings, name) {
  return standings.find((s) => s.name === name);
}

function _applyResult(match, standings) {
  const { score1: s1, score2: s2, p1, p2 } = match;
  if (s1 == null || s2 == null) return;
  if (s1 > s2) {
    _findStanding(standings, p1).points += 3;
  } else if (s2 > s1) {
    _findStanding(standings, p2).points += 3;
  } else {
    _findStanding(standings, p1).points += 1;
    _findStanding(standings, p2).points += 1;
  }
  _findStanding(standings, p1).gd += s1 - s2;
  _findStanding(standings, p2).gd += s2 - s1;
}

function _revertResult(match, standings) {
  const { score1: s1, score2: s2, p1, p2 } = match;
  if (s1 == null || s2 == null) return;
  if (s1 > s2) {
    _findStanding(standings, p1).points -= 3;
  } else if (s2 > s1) {
    _findStanding(standings, p2).points -= 3;
  } else {
    _findStanding(standings, p1).points -= 1;
    _findStanding(standings, p2).points -= 1;
  }
  _findStanding(standings, p1).gd -= s1 - s2;
  _findStanding(standings, p2).gd -= s2 - s1;
}

function _playersKnown(match) {
  const p1 = match.p1;
  const p2 = match.p2;
  if (!p1 || !p2) return false;
  return !String(p1).startsWith('Winner') && !String(p2).startsWith('Winner');
}

// computeKnockoutBracket and updateKnockoutProgress are large functions.
// Ported mostly verbatim from Python for feature parity.

function _computeKnockoutBracket(sortedStandings) {
  const seeds = sortedStandings.map((s) => s.name);
  const n = seeds.length;
  if (n < 4) return null;
  const bracket = { size: n, seeds: seeds.slice() };
  let useSeeds = seeds.slice();
  if (n === 5) {
    useSeeds = seeds.slice(0, 4);
  } else if (n === 6) {
    useSeeds = seeds.slice(0, 5);
  } else if (n === 8) {
    useSeeds = seeds.slice(0, 7);
  } else if (n === 9) {
    useSeeds = seeds.slice(0, 8);
  } else if (n === 10) {
    useSeeds = seeds.slice(0, 8);
  } else if (n === 11) {
    useSeeds = seeds.slice(0, 10);
  } else if (n >= 12) {
    useSeeds = seeds.slice(0, 12);
  }
  const m = useSeeds.length;
  let playins = [];
  let qfs = [];
  let sfs = [];
  if (m <= 4) {
    sfs = [
      { p1: useSeeds[0], p2: useSeeds[3], score1: null, score2: null },
      { p1: useSeeds[1], p2: useSeeds[2], score1: null, score2: null },
    ];
  } else if (m === 5) {
    playins = [
      { p1: useSeeds[3], p2: useSeeds[4], score1: null, score2: null },
    ];
    sfs = [
      { p1: useSeeds[0], p2: `Winner of ${useSeeds[3]} vs ${useSeeds[4]}`, score1: null, score2: null },
      { p1: useSeeds[1], p2: useSeeds[2], score1: null, score2: null },
    ];
  } else if (m === 7) {
    qfs = [
      { p1: useSeeds[1], p2: useSeeds[6], score1: null, score2: null },
      { p1: useSeeds[2], p2: useSeeds[5], score1: null, score2: null },
      { p1: useSeeds[3], p2: useSeeds[4], score1: null, score2: null },
    ];
    sfs = [
      { p1: useSeeds[0], p2: null, score1: null, score2: null },
      { p1: null, p2: null, score1: null, score2: null },
    ];
  } else if (m === 8) {
    qfs = [
      { p1: useSeeds[0], p2: useSeeds[7], score1: null, score2: null },
      { p1: useSeeds[1], p2: useSeeds[6], score1: null, score2: null },
      { p1: useSeeds[2], p2: useSeeds[5], score1: null, score2: null },
      { p1: useSeeds[3], p2: useSeeds[4], score1: null, score2: null },
    ];
    sfs = [
      { p1: null, p2: null, score1: null, score2: null },
      { p1: null, p2: null, score1: null, score2: null },
    ];
  } else if (m === 10) {
    playins = [
      { p1: useSeeds[6], p2: useSeeds[9], score1: null, score2: null },
      { p1: useSeeds[7], p2: useSeeds[8], score1: null, score2: null },
    ];
    qfs = [
      { p1: useSeeds[0], p2: `Winner of ${useSeeds[7]} vs ${useSeeds[8]}`, score1: null, score2: null },
      { p1: useSeeds[1], p2: `Winner of ${useSeeds[6]} vs ${useSeeds[9]}`, score1: null, score2: null },
      { p1: useSeeds[2], p2: useSeeds[5], score1: null, score2: null },
      { p1: useSeeds[3], p2: useSeeds[4], score1: null, score2: null },
    ];
    sfs = [
      { p1: null, p2: null, score1: null, score2: null },
      { p1: null, p2: null, score1: null, score2: null },
    ];
  } else if (m === 12) {
    playins = [
      { p1: useSeeds[5], p2: useSeeds[10], score1: null, score2: null },
      { p1: useSeeds[6], p2: useSeeds[9], score1: null, score2: null },
      { p1: useSeeds[7], p2: useSeeds[8], score1: null, score2: null },
      { p1: useSeeds[11], p2: useSeeds[4], score1: null, score2: null },
    ];
    qfs = [
      { p1: useSeeds[0], p2: `Winner of ${useSeeds[7]} vs ${useSeeds[8]}`, score1: null, score2: null },
      { p1: useSeeds[1], p2: `Winner of ${useSeeds[6]} vs ${useSeeds[9]}`, score1: null, score2: null },
      { p1: useSeeds[2], p2: `Winner of ${useSeeds[5]} vs ${useSeeds[10]}`, score1: null, score2: null },
      { p1: useSeeds[3], p2: `Winner of ${useSeeds[11]} vs ${useSeeds[4]}`, score1: null, score2: null },
    ];
    sfs = [
      { p1: null, p2: null, score1: null, score2: null },
      { p1: null, p2: null, score1: null, score2: null },
    ];
  }
  const final = { p1: 'Winner of Semifinal 1', p2: 'Winner of Semifinal 2', score1: null, score2: null };
  if (playins.length) bracket.playins = playins;
  if (qfs.length) bracket.qfs = qfs;
  if (sfs.length) bracket.sfs = sfs;
  bracket.final = final;
  return bracket;
}

function _updateKnockoutProgress(bracket) {
  if (!bracket) return;
  const size = bracket.size || 0;
  const playinWinners = [];
  for (const m of bracket.playins || []) {
    const { score1: s1, score2: s2 } = m;
    if (s1 != null && s2 != null) playinWinners.push(s1 >= s2 ? m.p1 : m.p2);
    else playinWinners.push(null);
  }
  if (size === 6 && playinWinners[0]) {
    bracket.sfs[0].p2 = playinWinners[0];
  }
  if (size === 11 && playinWinners.length === 2) {
    if (playinWinners[1]) bracket.qfs[0].p2 = playinWinners[1];
    if (playinWinners[0]) bracket.qfs[1].p2 = playinWinners[0];
  }
  if (size >= 12 && playinWinners.length === 4) {
    if (playinWinners[2]) bracket.qfs[0].p2 = playinWinners[2];
    if (playinWinners[1]) bracket.qfs[1].p2 = playinWinners[1];
    if (playinWinners[0]) bracket.qfs[2].p2 = playinWinners[0];
    if (playinWinners[3]) bracket.qfs[3].p2 = playinWinners[3];
  }
  const winnersQf = [];
  for (const m of bracket.qfs || []) {
    const { score1: s1, score2: s2 } = m;
    if (s1 != null && s2 != null) {
      winnersQf.push(s1 >= s2 ? m.p1 : m.p2);
    } else {
      winnersQf.push(null);
    }
  }
  if (size === 7 && winnersQf.length === 3 && winnersQf.every(Boolean)) {
    const seedMap = {};
    bracket.seeds.slice(0, 7).forEach((p, i) => { seedMap[p] = i; });
    const winnersSorted = winnersQf.slice().sort((a, b) => (seedMap[a] || 100) - (seedMap[b] || 100));
    const lowest = winnersSorted[winnersSorted.length - 1];
    const others = winnersSorted.filter((w) => w !== lowest);
    bracket.sfs[0].p2 = lowest;
    bracket.sfs[1].p1 = others[0];
    bracket.sfs[1].p2 = others[1];
  } else if (size >= 8 && winnersQf.length >= 4) {
    if (winnersQf[0] && winnersQf[winnersQf.length - 1]) {
      bracket.sfs[0].p1 = winnersQf[0];
      bracket.sfs[0].p2 = winnersQf[winnersQf.length - 1];
    }
    if (winnersQf[1] && winnersQf[2]) {
      bracket.sfs[1].p1 = winnersQf[1];
      bracket.sfs[1].p2 = winnersQf[2];
    }
  }
  const winnersSf = [];
  for (const m of bracket.sfs || []) {
    const { score1: s1, score2: s2, p1, p2 } = m;
    if (p1 && p2 && s1 != null && s2 != null) {
      winnersSf.push(s1 >= s2 ? p1 : p2);
    }
  }
  if (winnersSf.length === 2 && bracket.final) {
    bracket.final.p1 = winnersSf[0];
    bracket.final.p2 = winnersSf[1];
  }
}

module.exports = {
  drawGroup,
  scheduleRoundRobin,
  _applyResult,
  _revertResult,
  _playersKnown,
  _computeKnockoutBracket,
  _updateKnockoutProgress,
};
