// Front-end logic for adding players and creating tournament without page reload

document.addEventListener('DOMContentLoaded', () => {
  const players = [];
  const addForm = document.getElementById('add-player-form');
  const playerInput = document.getElementById('player-name');
  const playerList = document.getElementById('player-list');
  const playersField = document.getElementById('players-json');
  const noPlayers = document.getElementById('no-players');
  const createForm = document.getElementById('create-form');
  const titleInput = document.getElementById('tournament-title');
  const createTitle = document.getElementById('create-title');

  function renderPlayers() {
    playerList.innerHTML = '';
    players.forEach((p, idx) => {
      const li = document.createElement('li');
      li.textContent = p;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = 'Remove';
      btn.className = 'styled-button danger-button';
      btn.addEventListener('click', () => {
        players.splice(idx, 1);
        renderPlayers();
      });
      li.appendChild(btn);
      playerList.appendChild(li);
    });
    playersField.value = JSON.stringify(players);
    noPlayers.style.display = players.length ? 'none' : 'block';
  }

  addForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = playerInput.value.trim();
    if (name) {
      players.push(name);
      playerInput.value = '';
      renderPlayers();
    }
  });

  createForm.addEventListener('submit', () => {
    createTitle.value = titleInput.value.trim();
  });

  renderPlayers();
});
