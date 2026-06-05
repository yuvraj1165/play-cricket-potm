"""
Play Cricket Player Insights
Fetches all matches for the season, finds a specific player's appearances,
and generates performance insights.
"""

import json
import sys
import os
from datetime import datetime

# Reuse shared config and API functions from the POTM script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_cricket_mcp import (
    api_request, SITE_ID, SEASON,
    fetch_matches, fetch_match_detail, get_api_token
)


def find_player_in_match(match_detail, player_id):
    """Search a match scorecard for a specific player and extract their performance."""
    match = match_detail.get("match_details", [{}])[0] if "match_details" in match_detail else match_detail

    result_desc = match.get("result_description", "")
    result = match.get("result", "")
    match_date = match.get("match_date", "")
    home_club = match.get("home_club_name", "")
    away_club = match.get("away_club_name", "")
    home_team_id = match.get("home_team_id", "")

    if result == "A":  # Abandoned
        return None

    innings_list = match.get("innings", [])
    if not innings_list:
        return None

    # Determine winning team
    winning_team = ""
    if "Won" in result_desc:
        winning_team = result_desc.split(" - ")[0].strip() if " - " in result_desc else ""

    batting_perf = None
    bowling_perf = None
    fielding = {"catches": 0, "run_outs": 0, "stumpings": 0}
    player_team = ""
    player_id_str = str(player_id)

    for innings in innings_list:
        team_batting_id = innings.get("team_batting_id", "")
        batting_team = home_club if team_batting_id == home_team_id else away_club
        bowling_team = away_club if team_batting_id == home_team_id else home_club

        # Check batting
        for bat in innings.get("bat", []):
            if str(bat.get("batsman_id", "")) == player_id_str:
                if bat.get("how_out") == "did not bat":
                    continue
                runs = int(bat.get("runs", 0) or 0)
                balls = int(bat.get("balls", 0) or 0)
                fours = int(bat.get("fours", 0) or 0)
                sixes = int(bat.get("sixes", 0) or 0)
                not_out = bat.get("how_out") == "not out"
                player_team = batting_team

                # Keep best innings if multiple (shouldn't happen in limited overs)
                if batting_perf is None or runs > batting_perf["runs"]:
                    batting_perf = {
                        "runs": runs,
                        "balls": balls,
                        "fours": fours,
                        "sixes": sixes,
                        "not_out": not_out,
                        "strike_rate": round((runs / balls) * 100, 2) if balls > 0 else 0
                    }

        # Check bowling
        for bowl in innings.get("bowl", []):
            if str(bowl.get("bowler_id", "")) == player_id_str:
                overs_str = str(bowl.get("overs", "0") or "0").strip()
                wickets = int(bowl.get("wickets", 0) or 0)
                runs_conceded = int(bowl.get("runs", 0) or 0)
                maidens = int(bowl.get("maidens", 0) or 0)
                player_team = bowling_team

                if bowling_perf is None or wickets > bowling_perf["wickets"]:
                    bowling_perf = {
                        "overs": overs_str,
                        "wickets": wickets,
                        "runs": runs_conceded,
                        "maidens": maidens
                    }

        # Check fielding
        for bat in innings.get("bat", []):
            fielder_id = str(bat.get("fielder_id", "")).strip()
            if fielder_id == player_id_str:
                how_out = bat.get("how_out", "").lower()
                if "ct" in how_out:
                    fielding["catches"] += 1
                elif "run out" in how_out:
                    fielding["run_outs"] += 1
                elif "st" in how_out:
                    fielding["stumpings"] += 1
                if not player_team:
                    player_team = bowling_team

    if not batting_perf and not bowling_perf and sum(fielding.values()) == 0:
        return None

    won_match = winning_team and winning_team in player_team

    return {
        "date": match_date,
        "home": home_club,
        "away": away_club,
        "team": player_team,
        "opponent": away_club if player_team == home_club else home_club,
        "result": result_desc,
        "won": won_match,
        "batting": batting_perf,
        "bowling": bowling_perf,
        "fielding": fielding
    }


def generate_insights(player_id, performances):
    """Generate aggregated insights from all performances."""
    total_matches = len(performances)
    wins = sum(1 for p in performances if p["won"])
    losses = total_matches - wins

    # Batting stats
    batting_innings = [p for p in performances if p["batting"]]
    total_runs = sum(p["batting"]["runs"] for p in batting_innings)
    total_balls = sum(p["batting"]["balls"] for p in batting_innings)
    not_outs = sum(1 for p in batting_innings if p["batting"]["not_out"])
    dismissals = len(batting_innings) - not_outs
    highest = max((p["batting"]["runs"] for p in batting_innings), default=0)
    total_fours = sum(p["batting"]["fours"] for p in batting_innings)
    total_sixes = sum(p["batting"]["sixes"] for p in batting_innings)
    fifties = sum(1 for p in batting_innings if 50 <= p["batting"]["runs"] < 100)
    hundreds = sum(1 for p in batting_innings if p["batting"]["runs"] >= 100)
    ducks = sum(1 for p in batting_innings if p["batting"]["runs"] == 0 and not p["batting"]["not_out"])

    bat_avg = round(total_runs / dismissals, 2) if dismissals > 0 else float('inf')
    bat_sr = round((total_runs / total_balls) * 100, 2) if total_balls > 0 else 0

    # Bowling stats
    bowling_innings = [p for p in performances if p["bowling"]]
    total_wickets = sum(p["bowling"]["wickets"] for p in bowling_innings)
    total_runs_conceded = sum(p["bowling"]["runs"] for p in bowling_innings)
    total_maidens = sum(p["bowling"]["maidens"] for p in bowling_innings)
    best_bowling = None
    if bowling_innings:
        best_bowling = max(bowling_innings, key=lambda p: (p["bowling"]["wickets"], -p["bowling"]["runs"]))
    three_fers = sum(1 for p in bowling_innings if p["bowling"]["wickets"] >= 3)
    five_fers = sum(1 for p in bowling_innings if p["bowling"]["wickets"] >= 5)

    # Parse total overs bowled
    total_balls_bowled = 0
    for p in bowling_innings:
        overs_str = p["bowling"]["overs"]
        if not overs_str or overs_str == "0":
            continue
        if "." in overs_str:
            full, extra = overs_str.split(".")
            total_balls_bowled += int(full) * 6 + int(extra)
        else:
            total_balls_bowled += int(float(overs_str)) * 6

    bowl_avg = round(total_runs_conceded / total_wickets, 2) if total_wickets > 0 else float('inf')
    bowl_econ = round(total_runs_conceded / (total_balls_bowled / 6), 2) if total_balls_bowled > 0 else 0
    bowl_sr = round(total_balls_bowled / total_wickets, 2) if total_wickets > 0 else float('inf')

    # Fielding
    total_catches = sum(p["fielding"]["catches"] for p in performances)
    total_run_outs = sum(p["fielding"]["run_outs"] for p in performances)
    total_stumpings = sum(p["fielding"]["stumpings"] for p in performances)

    # Print report
    print(f"\n{'='*60}")
    print(f"📊 PLAYER INSIGHTS — ID: {player_id}")
    print(f"{'='*60}")
    if performances:
        print(f"Team: {performances[0]['team']}")
    print(f"Matches: {total_matches} | Won: {wins} | Lost: {losses} | Win%: {round(wins/total_matches*100)}%\n")

    # Batting
    print(f"🏏 BATTING")
    print(f"{'─'*40}")
    print(f"Innings: {len(batting_innings)} | Not Outs: {not_outs}")
    print(f"Runs: {total_runs} | Highest: {highest}")
    print(f"Average: {bat_avg} | Strike Rate: {bat_sr}")
    print(f"50s: {fifties} | 100s: {hundreds} | Ducks: {ducks}")
    print(f"4s: {total_fours} | 6s: {total_sixes} | Boundaries: {total_fours + total_sixes}")

    # Bowling
    if bowling_innings:
        print(f"\n🎳 BOWLING")
        print(f"{'─'*40}")
        print(f"Innings: {len(bowling_innings)} | Overs: {total_balls_bowled // 6}.{total_balls_bowled % 6}")
        print(f"Wickets: {total_wickets} | Maidens: {total_maidens}")
        print(f"Average: {bowl_avg} | Economy: {bowl_econ} | SR: {bowl_sr}")
        print(f"3-fers: {three_fers} | 5-fers: {five_fers}")
        if best_bowling:
            bb = best_bowling["bowling"]
            print(f"Best: {bb['wickets']}/{bb['runs']} ({bb['overs']} ov) vs {best_bowling['opponent']} on {best_bowling['date']}")

    # Fielding
    total_dismissals = total_catches + total_run_outs + total_stumpings
    if total_dismissals > 0:
        print(f"\n🧤 FIELDING")
        print(f"{'─'*40}")
        print(f"Catches: {total_catches} | Run Outs: {total_run_outs} | Stumpings: {total_stumpings}")

    # Match-by-match breakdown
    print(f"\n📅 MATCH-BY-MATCH")
    print(f"{'─'*60}")
    print(f"{'Date':<12} {'Opponent':<25} {'Bat':<15} {'Bowl':<12} {'W/L'}")
    print(f"{'─'*60}")
    for p in performances:
        bat_str = ""
        if p["batting"]:
            no = "*" if p["batting"]["not_out"] else ""
            bat_str = f"{p['batting']['runs']}{no}({p['batting']['balls']}b)"
        bowl_str = ""
        if p["bowling"]:
            bowl_str = f"{p['bowling']['wickets']}/{p['bowling']['runs']}"
        wl = "✅" if p["won"] else "❌"
        print(f"{p['date']:<12} {p['opponent']:<25} {bat_str:<15} {bowl_str:<12} {wl}")

    # Performance in wins vs losses
    wins_batting = [p for p in batting_innings if p["won"]]
    losses_batting = [p for p in batting_innings if not p["won"]]
    if wins_batting and losses_batting:
        avg_in_wins = sum(p["batting"]["runs"] for p in wins_batting) / len(wins_batting)
        avg_in_losses = sum(p["batting"]["runs"] for p in losses_batting) / len(losses_batting)
        print(f"\n📈 CONTEXT")
        print(f"{'─'*40}")
        print(f"Avg runs in wins: {avg_in_wins:.1f}")
        print(f"Avg runs in losses: {avg_in_losses:.1f}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Play Cricket Player Insights")
    parser.add_argument("player_id", help="Player ID from Play Cricket")
    parser.add_argument("--season", default=SEASON, help="Season year (default: current)")
    args = parser.parse_args()

    player_id = args.player_id
    print(f"Fetching all matches for season {args.season}...")

    # Fetch all matches (no date filter)
    data = api_request("matches.json", {"site_id": SITE_ID, "season": args.season})
    all_matches = data.get("matches", [])
    print(f"Found {len(all_matches)} total matches in season {args.season}")

    # Fetch each match detail and look for the player
    print(f"Scanning scorecards for player ID {player_id}...")
    performances = []

    for i, match in enumerate(all_matches):
        mid = match.get("id") or match.get("match_id")
        if not mid:
            continue
        detail = fetch_match_detail(mid)
        perf = find_player_in_match(detail, player_id)
        if perf:
            performances.append(perf)
        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Scanned {i+1}/{len(all_matches)} matches ({len(performances)} appearances found)...")

    print(f"\nFound {len(performances)} appearances for player {player_id}")

    if not performances:
        print("No appearances found. Check the player ID is correct.")
        return

    # Sort by date
    performances.sort(key=lambda p: p["date"])

    generate_insights(player_id, performances)


if __name__ == "__main__":
    main()
