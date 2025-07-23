import random
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Match:
    p1: str
    p2: str
    score1: Optional[int] = None
    score2: Optional[int] = None
    round: int = 0

@dataclass
class Standing:
    name: str
    points: int = 0
    gd: int = 0

def draw_group(players: List[str]) -> List[str]:
    """Randomly shuffle players into a single group."""
    random.shuffle(players)
    return players

def schedule_round_robin(players: List[str]) -> List[Match]:
    """Create a round-robin schedule returning matches with round numbers."""
    players = players.copy()
    if len(players) % 2 == 1:
        players.append(None)
    n = len(players)
    rounds: List[Match] = []
    for r in range(n - 1):
        for i in range(n // 2):
            p1 = players[i]
            p2 = players[n - 1 - i]
            if p1 is not None and p2 is not None:
                rounds.append(Match(p1, p2, round=r + 1))
        # rotate list except the first element
        players = [players[0]] + players[-1:] + players[1:-1]
    return rounds

def input_score(prompt: str) -> int:
    while True:
        s = input(prompt)
        try:
            return int(s)
        except ValueError:
            print("Please enter a number.")

def play_group(matches: List[Match], standings: List[Standing]):
    for m in matches:
        print(f"\n{m.p1} vs {m.p2}")
        m.score1 = input_score(f"  {m.p1} score: ")
        m.score2 = input_score(f"  {m.p2} score: ")
        if m.score1 > m.score2:
            standings_by_name(standings, m.p1).points += 3
        elif m.score2 > m.score1:
            standings_by_name(standings, m.p2).points += 3
        else:
            standings_by_name(standings, m.p1).points += 1
            standings_by_name(standings, m.p2).points += 1
        standings_by_name(standings, m.p1).gd += m.score1 - m.score2
        standings_by_name(standings, m.p2).gd += m.score2 - m.score1

def standings_by_name(standings: List[Standing], name: str) -> Standing:
    for s in standings:
        if s.name == name:
            return s
    raise ValueError("player not found")

def display_standings(title: str, standings: List[Standing]):
    print(f"\n{title}")
    sorted_s = sorted(standings, key=lambda s: (-s.points, -s.gd))
    for s in sorted_s:
        print(f"{s.name:10} Pts:{s.points:2} GD:{s.gd:3}")

def knockout_bracket(all_standings: List[Standing]):
    ranked = sorted(all_standings, key=lambda s: (-s.points, -s.gd))[:7]
    bye = ranked[0].name
    others = [s.name for s in ranked[1:]]
    qfs = [
        Match(others[0], others[5]),
        Match(others[1], others[4]),
        Match(others[2], others[3]),
    ]
    sfs = [
        Match(bye, None),
        Match(None, None)
    ]
    final = Match(None, None)

    winners = []
    # quarterfinals
    print("\nQuarterfinals")
    for i, m in enumerate(qfs):
        print(f"{m.p1} vs {m.p2}")
        m.score1 = input_score(f"  {m.p1} score: ")
        m.score2 = input_score(f"  {m.p2} score: ")
        winners.append(m.p1 if m.score1 >= m.score2 else m.p2)
    sfs[0].p2 = winners[2]
    sfs[1].p1, sfs[1].p2 = winners[0], winners[1]

    sf_winners = []
    print("\nSemifinals")
    for i, m in enumerate(sfs):
        print(f"{m.p1} vs {m.p2}")
        m.score1 = input_score(f"  {m.p1} score: ")
        m.score2 = input_score(f"  {m.p2} score: ")
        sf_winners.append(m.p1 if m.score1 >= m.score2 else m.p2)
    final.p1, final.p2 = sf_winners[0], sf_winners[1]

    print("\nFinal")
    print(f"{final.p1} vs {final.p2}")
    final.score1 = input_score(f"  {final.p1} score: ")
    final.score2 = input_score(f"  {final.p2} score: ")
    champion = final.p1 if final.score1 >= final.score2 else final.p2

    print(f"\nChampion: {champion}\n")

def main():
    print("Darts Tournament Manager (CLI)")
    players = []
    for i in range(8):
        name = input(f"Enter player {i+1} name: ").strip()
        players.append(name)

    group_a = draw_group(players)
    print(f"\nGroup A: {', '.join(group_a)}")

    matches_a = schedule_round_robin(group_a)
    standings_a = [Standing(name) for name in group_a]

    print("\n--- Group Stage ---")
    print("\nGroup A matches")
    play_group(matches_a, standings_a)

    display_standings("Group A Standings", standings_a)

    combined = standings_a
    knockout_bracket(combined)

if __name__ == "__main__":
    main()
