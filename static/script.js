const playerForm = document.getElementById('player-form');
const playerInputsDiv = document.getElementById('player-inputs');
const groupStageSection = document.getElementById('group-stage');
const groupsDiv = document.getElementById('groups');
const groupMatchesDiv = document.getElementById('group-matches');
const startKnockoutBtn = document.getElementById('start-knockout');
const knockoutSection = document.getElementById('knockout-stage');
const knockoutBracketDiv = document.getElementById('knockout-bracket');

let players = [];
let groups = { A: [], B: [] };
let groupMatches = [];
let standings = { A: [], B: [] };
let knockoutMatches = [];

function createPlayerInputs() {
    playerInputsDiv.innerHTML = '';
    for (let i = 0; i < 8; i++) {
        const input = document.createElement('input');
        input.type = 'text';
        input.placeholder = `Player ${i + 1}`;
        input.required = true;
        playerInputsDiv.appendChild(input);
        playerInputsDiv.appendChild(document.createElement('br'));
    }
}

function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}

function drawGroups() {
    groupsDiv.innerHTML = '';
    groups = { A: [], B: [] };
    const shuffled = shuffle([...players]);
    groups.A = shuffled.slice(0, 4);
    groups.B = shuffled.slice(4, 8);
    ['A', 'B'].forEach(g => {
        const div = document.createElement('div');
        div.innerHTML = `<h3>Group ${g}</h3><ol>${groups[g].map(p => `<li>${p}</li>`).join('')}</ol>`;
        groupsDiv.appendChild(div);
    });
}

function scheduleGroupMatches() {
    groupMatches = [];
    standings = { A: [], B: [] };
    ['A', 'B'].forEach(g => {
        const group = groups[g];
        const matches = [];
        for (let i = 0; i < group.length; i++) {
            for (let j = i + 1; j < group.length; j++) {
                matches.push({
                    group: g,
                    p1: group[i],
                    p2: group[j],
                    score1: '',
                    score2: ''
                });
            }
        }
        groupMatches.push(...matches);
        standings[g] = group.map(name => ({ name, points: 0, gd: 0 }));
    });
    renderGroupMatches();
}

function renderGroupMatches() {
    groupMatchesDiv.innerHTML = '';
    groupMatches.forEach((match, idx) => {
        const div = document.createElement('div');
        div.innerHTML = `
            <span>${match.p1}</span>
            <input type="number" min="0" data-match="${idx}" data-field="score1" value="${match.score1}">
            <span>vs</span>
            <input type="number" min="0" data-match="${idx}" data-field="score2" value="${match.score2}">
            <span>${match.p2}</span>
        `;
        groupMatchesDiv.appendChild(div);
    });
    const updateBtn = document.createElement('button');
    updateBtn.textContent = 'Update Standings';
    updateBtn.onclick = updateStandings;
    groupMatchesDiv.appendChild(updateBtn);
}

function updateStandings() {
    const inputs = groupMatchesDiv.querySelectorAll('input');
    inputs.forEach(input => {
        const idx = parseInt(input.dataset.match);
        const field = input.dataset.field;
        groupMatches[idx][field] = input.value;
    });

    // reset standings
    ['A', 'B'].forEach(g => {
        standings[g].forEach(s => { s.points = 0; s.gd = 0; });
    });

    groupMatches.forEach(match => {
        if (match.score1 === '' || match.score2 === '') return;
        const score1 = parseInt(match.score1);
        const score2 = parseInt(match.score2);
        const s1 = standings[match.group].find(p => p.name === match.p1);
        const s2 = standings[match.group].find(p => p.name === match.p2);
        if (score1 > score2) {
            s1.points += 3;
        } else if (score2 > score1) {
            s2.points += 3;
        } else {
            s1.points += 1;
            s2.points += 1;
        }
        s1.gd += score1 - score2;
        s2.gd += score2 - score1;
    });

    renderStandings();

    const allEntered = groupMatches.every(m => m.score1 !== '' && m.score2 !== '');
    if (allEntered) {
        startKnockoutBtn.disabled = false;
    }
}

function renderStandings() {
    const tableDiv = document.createElement('div');
    ['A', 'B'].forEach(g => {
        const table = document.createElement('table');
        table.innerHTML = `<caption>Group ${g} Standings</caption>
            <tr><th>Player</th><th>Pts</th><th>GD</th></tr>`;
        const sorted = standings[g].slice().sort((a, b) => b.points - a.points || b.gd - a.gd);
        sorted.forEach(p => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${p.name}</td><td>${p.points}</td><td>${p.gd}</td>`;
            table.appendChild(tr);
        });
        tableDiv.appendChild(table);
    });
    groupsDiv.appendChild(tableDiv);
}

function startKnockout() {
    startKnockoutBtn.disabled = true;
    const combined = [...standings.A, ...standings.B];
    combined.sort((a, b) => b.points - a.points || b.gd - a.gd);
    const top7 = combined.slice(0, 7);
    const byePlayer = top7[0].name;
    const others = top7.slice(1);

    knockoutMatches = [
        { round: 'Quarterfinal', p1: others[0].name, p2: others[5].name, score1: '', score2: '' },
        { round: 'Quarterfinal', p1: others[1].name, p2: others[4].name, score1: '', score2: '' },
        { round: 'Quarterfinal', p1: others[2].name, p2: others[3].name, score1: '', score2: '' },
        { round: 'Semifinal', p1: byePlayer, p2: null, score1: '', score2: '' },
        { round: 'Semifinal', p1: null, p2: null, score1: '', score2: '' },
        { round: 'Final', p1: null, p2: null, score1: '', score2: '' }
    ];
    renderKnockout();
}

function renderKnockout() {
    knockoutBracketDiv.innerHTML = '';
    knockoutSection.style.display = 'block';

    knockoutMatches.forEach((m, idx) => {
        const div = document.createElement('div');
        const p2Name = m.p2 ? m.p2 : 'TBD';
        div.innerHTML = `<strong>${m.round}</strong>: ${m.p1} vs ${p2Name} `;
        if (m.round !== 'Final' || m.p1 && m.p2) {
            div.innerHTML += `<input type="number" min="0" data-kmatch="${idx}" data-field="score1" value="${m.score1}"> - `;
            div.innerHTML += `<input type="number" min="0" data-kmatch="${idx}" data-field="score2" value="${m.score2}">`;
        }
        knockoutBracketDiv.appendChild(div);
    });
    const updateBtn = document.createElement('button');
    updateBtn.textContent = 'Update Knockout';
    updateBtn.onclick = updateKnockout;
    knockoutBracketDiv.appendChild(updateBtn);
}

function updateKnockout() {
    const inputs = knockoutBracketDiv.querySelectorAll('input');
    inputs.forEach(input => {
        const idx = parseInt(input.dataset.kmatch);
        const field = input.dataset.field;
        knockoutMatches[idx][field] = input.value;
    });
    // propagate winners
    // QFs
    for (let i = 0; i < 3; i++) {
        const m = knockoutMatches[i];
        if (m.score1 === '' || m.score2 === '') continue;
        const winner = parseInt(m.score1) >= parseInt(m.score2) ? m.p1 : m.p2;
        if (i === 0) knockoutMatches[4].p1 = winner; // QF1 winner to SF2 p1
        if (i === 1) knockoutMatches[4].p2 = winner; // QF2 winner to SF2 p2
        if (i === 2) knockoutMatches[3].p2 = winner; // QF3 winner to SF1 p2 (byePlayer vs winner)
    }
    // SFs
    for (let i = 3; i < 5; i++) {
        const m = knockoutMatches[i];
        if (m.score1 === '' || m.score2 === '') continue;
        const winner = parseInt(m.score1) >= parseInt(m.score2) ? m.p1 : m.p2;
        if (i === 3) knockoutMatches[5].p1 = winner; // SF1 winner to Final p1
        if (i === 4) knockoutMatches[5].p2 = winner; // SF2 winner to Final p2
    }
    renderKnockout();
}

playerForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const inputs = playerForm.querySelectorAll('input[type=text]');
    players = [];
    inputs.forEach(inp => players.push(inp.value.trim()));
    playerForm.style.display = 'none';
    drawGroups();
    scheduleGroupMatches();
    groupStageSection.style.display = 'block';
});

startKnockoutBtn.addEventListener('click', startKnockout);

createPlayerInputs();
