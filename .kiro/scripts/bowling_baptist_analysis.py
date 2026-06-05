"""
Bowling Baptist CC — Season Analysis & NRR Optimisation
Fetches match data from Play Cricket API for site 288 and provides
overall performance insights and NRR improvement guidance.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from play_cricket_mcp import api_request, get_api_token


# Configuration
SITE_ID = "288"
SEASON = str(datetime.now().year)
COMPETITION_ID = "138199"
TEAM_ID = "28849"  # 1st XI
MAX_OVERS = 45  # 45-over league


def fetch_all_matches():
    """Fetch all matches for Bowling Baptist CC 1st XI in the current season."""
    data = api_request("matches.json", {"site_id": SITE_ID, "season": SEASON})
    matches = data.get("matches", [])
    # Filter to our competition AND our team (1st XI)
    filtered = []
    for m in matches:
        if str(m.get("competition_id", "")) != COMPETITION_ID:
            continue
        # Check if our team is home or away
        if str(m.get("home_team_id", "")) == TEAM_ID or str(m.get("away_team_id", "")) == TEAM_ID:
            filtered.append(m)
    return filtered


def parse_overs_to_balls(overs_str):
    """Convert overs string (e.g. '34.3') to total balls."""
    if not overs_str or overs_str == "0":
        return 0
    overs_str = str(overs_str).strip()
    if "." in overs_str:
        full, extra = overs_str.split(".")
        return int(full) * 6 + int(extra)
    return int(float(overs_str)) * 6


def balls_to_overs_str(balls):
    """Convert total balls to overs string (e.g. 207 -> '34.3')."""
    full = balls // 6
    extra = balls % 6
    if extra == 0:
        return str(full)
    return f"{full}.{extra}"


def analyse_match_nrr(match_detail):
    """Analyse a single match for NRR contribution."""
    match = match_detail.get("match_details", [{}])[0] if "match_details" in match_detail else match_detail

    result_desc = match.get("result_description", "")
    result = match.get("result", "")
    match_date = match.get("match_date", "")
    home_club = match.get("home_club_name", "")
    away_club = match.get("away_club_name", "")
    home_team_id = match.get("home_team_id", "")

    if result == "A":  # Abandoned
        # Still extract partial innings data for R/W calculation
        # but mark as abandoned so NRR can exclude it
        pass

    innings_list = match.get("innings", [])
    if len(innings_list) < 1:
        return None

    is_abandoned = result == "A"

    # Determine which team is "ours" using team ID
    our_team = None
    opponent = None
    if str(match.get("home_team_id", "")) == TEAM_ID:
        our_team = home_club
        opponent = away_club
    elif str(match.get("away_team_id", "")) == TEAM_ID:
        our_team = away_club
        opponent = home_club
    else:
        # Fallback
        our_team = home_club
        opponent = away_club

    # Parse innings
    our_runs = 0
    our_balls_faced = 0
    our_all_out = False
    our_wickets_lost = 0
    their_runs = 0
    their_balls_faced = 0
    their_all_out = False
    their_wickets_lost = 0

    for innings in innings_list:
        team_batting_id = innings.get("team_batting_id", "")
        batting_team = home_club if team_batting_id == home_team_id else away_club
        innings_runs = int(innings.get("runs", 0) or 0)
        innings_overs = str(innings.get("overs", "0") or "0")
        innings_wickets = int(innings.get("wickets", 0) or 0)

        innings_balls = parse_overs_to_balls(innings_overs)

        # Check if team was all out (10 wickets or max overs used)
        all_out = innings_wickets >= 10

        if batting_team == our_team:
            our_runs += innings_runs
            if all_out:
                our_balls_faced += MAX_OVERS * 6  # Use full allocation
                our_all_out = True
            else:
                our_balls_faced += innings_balls
            our_wickets_lost = innings_wickets
        else:
            their_runs += innings_runs
            if all_out:
                their_balls_faced += innings_balls  # Actual balls bowled to dismiss them
                their_all_out = True
            else:
                their_balls_faced += innings_balls
            their_wickets_lost = innings_wickets

    if our_balls_faced == 0 and our_wickets_lost == 0 and their_wickets_lost == 0:
        return None

    # Calculate NRR components (only for non-abandoned matches with both innings)
    if our_balls_faced > 0 and their_balls_faced > 0 and not is_abandoned:
        our_run_rate = our_runs / (our_balls_faced / 6)
        their_run_rate = their_runs / (their_balls_faced / 6)
        match_nrr = our_run_rate - their_run_rate
    else:
        our_run_rate = 0
        their_run_rate = 0
        match_nrr = 0

    # Calculate R/W differential (includes abandoned partial innings)
    our_rpw = our_runs / our_wickets_lost if our_wickets_lost > 0 else our_runs
    their_rpw = their_runs / their_wickets_lost if their_wickets_lost > 0 else their_runs
    match_rw_diff = our_rpw - their_rpw

    # Determine win/loss
    winning_team = ""
    if "Won" in result_desc:
        winning_team = result_desc.split(" - ")[0].strip() if " - " in result_desc else ""
    won = our_team and winning_team and winning_team in our_team

    return {
        "date": match_date,
        "opponent": opponent,
        "our_team": our_team,
        "our_runs": our_runs,
        "our_balls_faced": our_balls_faced,
        "our_all_out": our_all_out,
        "our_wickets_lost": our_wickets_lost,
        "their_runs": their_runs,
        "their_balls_faced": their_balls_faced,
        "their_all_out": their_all_out,
        "their_wickets_lost": their_wickets_lost,
        "our_run_rate": round(our_run_rate, 3),
        "their_run_rate": round(their_run_rate, 3),
        "match_nrr": round(match_nrr, 3),
        "our_rpw": round(our_rpw, 2),
        "their_rpw": round(their_rpw, 2),
        "match_rw_diff": round(match_rw_diff, 2),
        "result": result_desc,
        "won": won,
        "abandoned": is_abandoned
    }


def calculate_season_nrr(match_analyses):
    """Calculate overall season NRR from all matches."""
    total_runs_scored = 0
    total_balls_faced = 0
    total_runs_conceded = 0
    total_balls_bowled = 0

    for m in match_analyses:
        total_runs_scored += m["our_runs"]
        total_balls_faced += m["our_balls_faced"]
        total_runs_conceded += m["their_runs"]
        total_balls_bowled += m["their_balls_faced"]

    if total_balls_faced == 0 or total_balls_bowled == 0:
        return 0

    season_rr_scored = total_runs_scored / (total_balls_faced / 6)
    season_rr_conceded = total_runs_conceded / (total_balls_bowled / 6)
    return round(season_rr_scored - season_rr_conceded, 3)


def generate_nrr_recommendations(match_analyses, season_nrr):
    """Generate NRR improvement recommendations."""
    recs = []

    # Identify matches that hurt NRR
    negative_matches = [m for m in match_analyses if m["match_nrr"] < 0]
    positive_matches = [m for m in match_analyses if m["match_nrr"] > 0]

    recs.append(f"\n{'='*60}")
    recs.append(f"📊 NRR IMPROVEMENT RECOMMENDATIONS")
    recs.append(f"{'='*60}\n")
    recs.append(f"Current Season NRR: {season_nrr:+.3f}")
    recs.append(f"Matches helping NRR: {len(positive_matches)}")
    recs.append(f"Matches hurting NRR: {len(negative_matches)}\n")

    if negative_matches:
        recs.append("⚠️ Matches that hurt NRR most:")
        worst = sorted(negative_matches, key=lambda m: m["match_nrr"])
        for m in worst[:3]:
            recs.append(f"  • {m['date']} vs {m['opponent']}: NRR {m['match_nrr']:+.3f}")
            recs.append(f"    Scored {m['our_runs']} off {balls_to_overs_str(m['our_balls_faced'])} ov "
                       f"(RR {m['our_run_rate']:.2f}) | "
                       f"Conceded {m['their_runs']} off {balls_to_overs_str(m['their_balls_faced'])} ov "
                       f"(RR {m['their_run_rate']:.2f})")

    recs.append(f"\n💡 TO IMPROVE NRR:")
    recs.append(f"{'─'*40}")
    recs.append(f"1. BATTING FIRST: Aim for 250+ in 45 overs (RR 5.5+)")
    recs.append(f"   Then bowl opposition out as quickly as possible")
    recs.append(f"2. CHASING: Win with maximum overs to spare")
    recs.append(f"   e.g. Chasing 180, win in 30 overs = RR 6.0 vs conceding RR 4.0")
    recs.append(f"3. BOWLING: Take all 10 wickets — their overs count as actual balls bowled")
    recs.append(f"   If bowled out in 35 overs, their RR calculated on 35 (higher = worse for them)")
    recs.append(f"4. AVOID: Slow batting (especially getting bowled out)")
    recs.append(f"   If bowled out, your overs count as full {MAX_OVERS} (RR drops significantly)")

    # What-if scenario for next match
    total_runs_scored = sum(m["our_runs"] for m in match_analyses)
    total_balls_faced = sum(m["our_balls_faced"] for m in match_analyses)
    total_runs_conceded = sum(m["their_runs"] for m in match_analyses)
    total_balls_bowled = sum(m["their_balls_faced"] for m in match_analyses)

    recs.append(f"\n📈 WHAT-IF SCENARIOS (next match):")
    recs.append(f"{'─'*40}")

    scenarios = [
        ("Win by 50 runs (bat first 220, bowl them out for 170 in 38 ov)", 220, MAX_OVERS * 6, 170, 38 * 6),
        ("Win by 100 runs (bat first 260, bowl them out for 160 in 35 ov)", 260, MAX_OVERS * 6, 160, 35 * 6),
        ("Chase 180 in 30 overs", 180, 30 * 6, 180, MAX_OVERS * 6),
        ("Chase 200 in 35 overs", 200, 35 * 6, 200, MAX_OVERS * 6),
    ]

    for desc, our_r, our_b, their_r, their_b in scenarios:
        new_total_scored = total_runs_scored + our_r
        new_total_faced = total_balls_faced + our_b
        new_total_conceded = total_runs_conceded + their_r
        new_total_bowled = total_balls_bowled + their_b
        new_nrr = (new_total_scored / (new_total_faced / 6)) - (new_total_conceded / (new_total_bowled / 6))
        change = new_nrr - season_nrr
        recs.append(f"  • {desc}")
        recs.append(f"    New NRR: {new_nrr:+.3f} (change: {change:+.3f})")

    return "\n".join(recs)


def main():
    print(f"{'='*60}")
    print(f"🏏 BOWLING BAPTIST CC — SEASON ANALYSIS & NRR")
    print(f"{'='*60}")
    print(f"Season: {SEASON} | Site ID: {SITE_ID} | Competition: {COMPETITION_ID}")
    print(f"Format: {MAX_OVERS} overs\n")

    # Fetch matches
    print("Fetching matches...")
    matches = fetch_all_matches()
    print(f"Found {len(matches)} matches in competition {COMPETITION_ID}\n")

    if not matches:
        print("No matches found.")
        return

    # Analyse each match
    match_analyses = []
    for match in matches:
        mid = match.get("id") or match.get("match_id")
        if not mid:
            continue
        detail = api_request("match_detail.json", {"match_id": str(mid)})
        analysis = analyse_match_nrr(detail)
        if analysis:
            match_analyses.append(analysis)

    if not match_analyses:
        print("No completed matches with scorecards found.")
        return

    # Sort by date
    match_analyses.sort(key=lambda m: m["date"])

    # Separate completed and abandoned matches
    completed_matches = [m for m in match_analyses if not m["abandoned"]]
    all_matches_for_rw = match_analyses  # Includes abandoned partial innings

    # Season summary
    total_matches = len(match_analyses)
    completed_count = len(completed_matches)
    abandoned_count = total_matches - completed_count
    wins = sum(1 for m in completed_matches if m["won"])
    losses = completed_count - wins

    print(f"📋 SEASON SUMMARY")
    print(f"{'─'*40}")
    print(f"Matches played: {total_matches} ({completed_count} completed, {abandoned_count} abandoned)")
    print(f"Won: {wins} | Lost: {losses} | Win%: {round(wins/completed_count*100) if completed_count > 0 else 0}%\n")

    # NRR breakdown per match (completed only)
    print(f"📊 NRR BREAKDOWN PER MATCH (completed matches only)")
    print(f"{'─'*60}")
    print(f"{'Date':<12} {'Opponent':<25} {'Our RR':<8} {'Their RR':<9} {'NRR':<8} {'W/L'}")
    print(f"{'─'*60}")

    for m in completed_matches:
        wl = "✅" if m["won"] else "❌"
        print(f"{m['date']:<12} {m['opponent']:<25} {m['our_run_rate']:<8.2f} {m['their_run_rate']:<9.2f} {m['match_nrr']:+.3f}  {wl}")

    # Batting & bowling summaries
    total_scored = sum(m["our_runs"] for m in completed_matches)
    total_faced = sum(m["our_balls_faced"] for m in completed_matches)
    total_conceded = sum(m["their_runs"] for m in completed_matches)
    total_bowled = sum(m["their_balls_faced"] for m in completed_matches)

    # Season NRR (completed matches only)
    season_nrr = calculate_season_nrr(completed_matches)
    print(f"\n{'─'*60}")
    print(f"SEASON NRR: {season_nrr:+.3f} (based on {completed_count} completed matches)")
    print(f"{'─'*60}")

    # R/W Differential breakdown (includes abandoned partial innings — matches league table)
    print(f"\n📊 RUNS/WICKET DIFFERENTIAL (includes abandoned — matches league table)")
    print(f"{'─'*60}")
    print(f"{'Date':<12} {'Opponent':<25} {'Our R/W':<8} {'Their R/W':<9} {'Diff':<8} {'Status'}")
    print(f"{'─'*60}")

    for m in all_matches_for_rw:
        status = "🚫 ABD" if m["abandoned"] else ("✅" if m["won"] else "❌")
        if m["our_wickets_lost"] > 0 or m["their_wickets_lost"] > 0:
            print(f"{m['date']:<12} {m['opponent']:<25} {m['our_rpw']:<8.2f} {m['their_rpw']:<9.2f} {m['match_rw_diff']:+.2f}   {status}")
        else:
            print(f"{m['date']:<12} {m['opponent']:<25} {'N/A':<8} {'N/A':<9} {'N/A':<8} {status}")

    # Season R/W differential (all matches including abandoned)
    total_scored_rw = sum(m["our_runs"] for m in all_matches_for_rw)
    total_our_wkts = sum(m["our_wickets_lost"] for m in all_matches_for_rw)
    total_conceded_rw = sum(m["their_runs"] for m in all_matches_for_rw)
    total_their_wkts = sum(m["their_wickets_lost"] for m in all_matches_for_rw)
    season_our_rpw = total_scored_rw / total_our_wkts if total_our_wkts > 0 else 0
    season_their_rpw = total_conceded_rw / total_their_wkts if total_their_wkts > 0 else 0
    season_rw_diff = season_our_rpw - season_their_rpw
    print(f"\n{'─'*60}")
    print(f"SEASON R/W DIFFERENTIAL: {season_rw_diff:+.2f} (league table shows: -1.65)")
    print(f"  Our R/W: {season_our_rpw:.2f} ({total_scored_rw} runs / {total_our_wkts} wkts)")
    print(f"  Their R/W: {season_their_rpw:.2f} ({total_conceded_rw} runs / {total_their_wkts} wkts)")
    print(f"{'─'*60}")

    print(f"\n🏏 BATTING: {total_scored} runs in {balls_to_overs_str(total_faced)} overs (RR {total_scored/(total_faced/6):.2f})")
    print(f"🎳 BOWLING: {total_conceded} conceded in {balls_to_overs_str(total_bowled)} overs (RR {total_conceded/(total_bowled/6):.2f})")

    # Recommendations
    print(generate_nrr_recommendations(match_analyses, season_nrr))


if __name__ == "__main__":
    main()
