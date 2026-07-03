"""
Opponent Analysis — Fetch and analyse match results for team 101153
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_cricket_mcp import api_request

MATCH_IDS = [
    "7497245", "7497243", "7505019", "7497126", "7505011",
    "7691631", "7497240", "7504996", "7497118", "7504993", "7497113"
]

TARGET_TEAM_ID = "101153"


def analyse_match(match_detail):
    """Parse a match detail and return a summary."""
    match = match_detail.get("match_details", [{}])[0] if "match_details" in match_detail else match_detail

    match_date = match.get("match_date", "")
    home_club = match.get("home_club_name", "")
    away_club = match.get("away_club_name", "")
    home_team_id = str(match.get("home_team_id", ""))
    away_team_id = str(match.get("away_team_id", ""))
    result_desc = match.get("result_description", "")
    result = match.get("result", "")

    # Determine which team is the target
    if home_team_id == TARGET_TEAM_ID:
        target_team_name = home_club
        opponent_name = away_club
        target_is_home = True
    elif away_team_id == TARGET_TEAM_ID:
        target_team_name = away_club
        opponent_name = home_club
        target_is_home = False
    else:
        # Try matching in innings
        target_team_name = "Unknown"
        opponent_name = "Unknown"
        target_is_home = None

    innings_list = match.get("innings", [])

    target_innings = []
    opponent_innings = []

    for inn in innings_list:
        team_batting_id = str(inn.get("team_batting_id", ""))
        batting_team = home_club if team_batting_id == home_team_id else away_club

        runs = int(inn.get("runs", 0) or 0)
        wickets = int(inn.get("wickets", 0) or 0)
        overs = inn.get("overs", "0")

        # Get top batsmen
        batsmen = inn.get("bat", [])
        top_bats = []
        for b in sorted(batsmen, key=lambda x: int(x.get("runs", 0) or 0), reverse=True)[:3]:
            name = b.get("batsman_name", "Unknown")
            b_runs = b.get("runs", "0")
            b_balls = b.get("balls_faced", "0")
            b_fours = b.get("fours", "0")
            b_sixes = b.get("sixes", "0")
            how_out = b.get("how_out", "")
            not_out = "*" if how_out and "not out" in how_out.lower() else ""
            top_bats.append(f"{name} {b_runs}{not_out}({b_balls}b, {b_fours}x4, {b_sixes}x6)")

        # Get top bowlers
        bowlers = inn.get("bowl", [])
        top_bowls = []
        for bw in sorted(bowlers, key=lambda x: int(x.get("wickets", 0) or 0), reverse=True)[:3]:
            name = bw.get("bowler_name", "Unknown")
            bw_wkts = bw.get("wickets", "0")
            bw_runs = bw.get("runs", "0")
            bw_overs = bw.get("overs", "0")
            bw_maidens = bw.get("maidens", "0")
            top_bowls.append(f"{name} {bw_wkts}/{bw_runs} ({bw_overs} ov, {bw_maidens}M)")

        inn_data = {
            "runs": runs,
            "wickets": wickets,
            "overs": overs,
            "top_batsmen": top_bats,
            "top_bowlers": top_bowls
        }

        if (target_is_home and team_batting_id == home_team_id) or \
           (not target_is_home and team_batting_id != home_team_id):
            target_innings.append(inn_data)
        else:
            opponent_innings.append(inn_data)

    # Did target team win?
    won = target_team_name in result_desc and "Won" in result_desc

    return {
        "date": match_date,
        "target_team": target_team_name,
        "opponent": opponent_name,
        "result": result_desc,
        "won": won,
        "abandoned": result == "A",
        "target_innings": target_innings,
        "opponent_innings": opponent_innings,
    }


def main():
    print(f"{'='*70}")
    print(f"🏏 OPPONENT ANALYSIS — Team ID {TARGET_TEAM_ID}")
    print(f"{'='*70}\n")

    results = []
    for mid in MATCH_IDS:
        print(f"Fetching match {mid}...")
        detail = api_request("match_detail.json", {"match_id": mid})
        analysis = analyse_match(detail)
        results.append(analysis)

    print(f"\nFound {len(results)} matches\n")
    print(f"{'='*70}")

    wins = 0
    losses = 0
    abandoned = 0

    for i, r in enumerate(results, 1):
        if r["abandoned"]:
            abandoned += 1
            status = "🚫 ABANDONED"
        elif r["won"]:
            wins += 1
            status = "✅ WON"
        else:
            losses += 1
            status = "❌ LOST"

        print(f"\n### Match {i}: {r['target_team']} vs {r['opponent']} ({r['date']})")
        print(f"**Result:** {r['result']} — {status}")

        if r["target_innings"]:
            for inn in r["target_innings"]:
                print(f"\n  🏏 {r['target_team']} Batting: {inn['runs']}/{inn['wickets']} ({inn['overs']} ov)")
                if inn["top_batsmen"]:
                    print(f"     Top bats: {' | '.join(inn['top_batsmen'])}")
                if inn["top_bowlers"]:
                    print(f"     Bowlers (opponent): {' | '.join(inn['top_bowlers'])}")

        if r["opponent_innings"]:
            for inn in r["opponent_innings"]:
                print(f"\n  🎳 {r['opponent']} Batting: {inn['runs']}/{inn['wickets']} ({inn['overs']} ov)")
                if inn["top_batsmen"]:
                    print(f"     Top bats: {' | '.join(inn['top_batsmen'])}")
                if inn["top_bowlers"]:
                    print(f"     Bowlers ({r['target_team']}): {' | '.join(inn['top_bowlers'])}")

        print(f"\n{'─'*70}")

    # Summary
    completed = wins + losses
    print(f"\n{'='*70}")
    print(f"📊 SEASON SUMMARY FOR TEAM {TARGET_TEAM_ID}")
    print(f"{'='*70}")
    print(f"Played: {len(results)} | Won: {wins} | Lost: {losses} | Abandoned: {abandoned}")
    if completed > 0:
        print(f"Win Rate: {wins/completed*100:.0f}%")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
