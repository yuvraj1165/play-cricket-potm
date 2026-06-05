"""
Play Cricket MCP Server
Fetches match data from Play Cricket API and analyses performances
to recommend Player of the Match for each group.
"""

import json
import sys
import os
from datetime import datetime, timedelta
from http.client import HTTPConnection, HTTPSConnection
from urllib.parse import urlencode


# Configuration
API_BASE = "www.play-cricket.com"
API_PATH = "/api/v2/"
SITE_ID = "262"
SEASON = str(datetime.now().year)
GROUP_A_COMPETITION_ID = "136363"
GROUP_B_COMPETITION_ID = "137864"

# Cup competition IDs
SJR_CUP_POOL_A_ID = "137059"
SJR_CUP_POOL_B_ID = "137060"
H_BROADBENT_TROPHY_POOL_A_ID = "137061"
H_BROADBENT_TROPHY_POOL_B_ID = "137062"

# T20 Cup competition IDs (Tuesday matches)
RIZUES_T20_GROUP_A_ID = "138140"
RIZUES_T20_GROUP_B_ID = "138141"
RIZUES_T20_GROUP_C_ID = "138142"

# Team abbreviations for WhatsApp poll (max 100 chars per option)
TEAM_ABBREVIATIONS = {
    "Apperley Bridge CC": "AB",
    "Allerton CC": "AL",
    "Awan CC": "AW",
    "Bradford Indians CC": "BI",
    "Bradford Kings CC": "BK",
    "Bradford Mavericks CC": "BM",
    "Bradford Phoenix CC": "BP",
    "Bradford Qalandars CC": "BQ",
    "Cambing CC": "CA",
    "Girlington CC": "GI",
    "Hallfield CC": "HF",
    "Kashmir (Bradford) CC": "KA",
    "Omars CC": "OM",
    "Salem Athletic CC": "SA",
    "Sunrise CC": "SU",
    "Yorkshire Friends CC": "YF",
}


def get_api_token():
    """Get API token from environment variable."""
    token = os.environ.get("PLAY_CRICKET_API_TOKEN")
    if not token:
        raise ValueError("PLAY_CRICKET_API_TOKEN environment variable not set")
    return token


def api_request(endpoint, params=None):
    """Make a request to the Play Cricket API."""
    token = get_api_token()
    if params is None:
        params = {}
    params["api_token"] = token

    path = f"{API_PATH}{endpoint}?{urlencode(params)}"
    conn = HTTPSConnection(API_BASE)
    conn.request("GET", path)
    response = conn.getresponse()

    # Follow redirects (301/302)
    if response.status in (301, 302):
        location = response.getheader("Location")
        conn.close()
        if location:
            from urllib.parse import urlparse
            parsed = urlparse(location)
            redirect_conn = HTTPSConnection(parsed.hostname)
            redirect_conn.request("GET", f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path)
            response = redirect_conn.getresponse()
            data = response.read().decode("utf-8")
            redirect_conn.close()
        else:
            raise Exception("API returned redirect with no Location header")
    else:
        data = response.read().decode("utf-8")
        conn.close()

    if response.status != 200:
        raise Exception(f"API request failed: {response.status} - {data[:200]}")

    return json.loads(data)


def get_last_saturday():
    """Get the date of last Saturday in DD/MM/YYYY format."""
    today = datetime.now()
    days_since_saturday = (today.weekday() + 2) % 7
    if days_since_saturday == 0:
        days_since_saturday = 7
    last_sat = today - timedelta(days=days_since_saturday)
    return last_sat.strftime("%d/%m/%Y")


def get_last_sunday():
    """Get the date of last Sunday in DD/MM/YYYY format."""
    today = datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    if days_since_sunday == 0:
        days_since_sunday = 7
    last_sun = today - timedelta(days=days_since_sunday)
    return last_sun.strftime("%d/%m/%Y")


def get_last_tuesday():
    """Get the date of last Tuesday in DD/MM/YYYY format."""
    today = datetime.now()
    days_since_tuesday = (today.weekday() - 1) % 7
    if days_since_tuesday == 0:
        days_since_tuesday = 7
    last_tue = today - timedelta(days=days_since_tuesday)
    return last_tue.strftime("%d/%m/%Y")


def fetch_matches(match_date=None):
    """Fetch all matches for the site and season, filtered by date."""
    data = api_request("matches.json", {"site_id": SITE_ID, "season": SEASON})

    matches = data.get("matches", [])

    if match_date:
        matches = [m for m in matches if m.get("match_date") == match_date]

    return matches


def fetch_match_detail(match_id):
    """Fetch full match details including scorecard."""
    data = api_request("match_detail.json", {"match_id": str(match_id)})
    return data


def categorize_matches(matches):
    """Split matches into Group A, Group B, cup competitions, and T20 groups."""
    group_a = []
    group_b = []
    sjr_cup_a = []
    sjr_cup_b = []
    broadbent_a = []
    broadbent_b = []
    t20_group_a = []
    t20_group_b = []
    t20_group_c = []

    for match in matches:
        comp_id = str(match.get("competition_id", ""))
        if comp_id == GROUP_A_COMPETITION_ID:
            group_a.append(match)
        elif comp_id == GROUP_B_COMPETITION_ID:
            group_b.append(match)
        elif comp_id == SJR_CUP_POOL_A_ID:
            sjr_cup_a.append(match)
        elif comp_id == SJR_CUP_POOL_B_ID:
            sjr_cup_b.append(match)
        elif comp_id == H_BROADBENT_TROPHY_POOL_A_ID:
            broadbent_a.append(match)
        elif comp_id == H_BROADBENT_TROPHY_POOL_B_ID:
            broadbent_b.append(match)
        elif comp_id == RIZUES_T20_GROUP_A_ID:
            t20_group_a.append(match)
        elif comp_id == RIZUES_T20_GROUP_B_ID:
            t20_group_b.append(match)
        elif comp_id == RIZUES_T20_GROUP_C_ID:
            t20_group_c.append(match)

    return group_a, group_b, sjr_cup_a, sjr_cup_b, broadbent_a, broadbent_b, t20_group_a, t20_group_b, t20_group_c


def analyse_batting(innings):
    """Extract batting performances from an innings."""
    performances = []
    for bat in innings.get("bat", []):
        if bat.get("how_out") == "did not bat":
            continue
        runs = int(bat.get("runs", 0) or 0)
        balls = int(bat.get("balls", 0) or 0)
        fours = int(bat.get("fours", 0) or 0)
        sixes = int(bat.get("sixes", 0) or 0)
        not_out = bat.get("how_out") == "not out"

        performances.append({
            "name": bat.get("batsman_name", ""),
            "id": bat.get("batsman_id", ""),
            "runs": runs,
            "balls": balls,
            "fours": fours,
            "sixes": sixes,
            "not_out": not_out,
            "strike_rate": round((runs / balls) * 100, 2) if balls > 0 else 0
        })

    return sorted(performances, key=lambda x: x["runs"], reverse=True)


def analyse_bowling(innings):
    """Extract bowling performances from an innings."""
    performances = []
    for bowl in innings.get("bowl", []):
        overs_str = str(bowl.get("overs", "0") or "0").strip()
        wickets = int(bowl.get("wickets", 0) or 0)
        runs = int(bowl.get("runs", 0) or 0)
        maidens = int(bowl.get("maidens", 0) or 0)

        # Parse overs (e.g., "5.2" = 5 overs 2 balls)
        if not overs_str or overs_str == "0":
            total_balls = 0
        elif "." in overs_str:
            full_overs, extra_balls = overs_str.split(".")
            total_balls = int(full_overs) * 6 + int(extra_balls)
        else:
            total_balls = int(float(overs_str)) * 6

        economy = round(runs / (total_balls / 6), 2) if total_balls > 0 else 0

        performances.append({
            "name": bowl.get("bowler_name", ""),
            "id": bowl.get("bowler_id", ""),
            "overs": overs_str,
            "maidens": maidens,
            "runs": runs,
            "wickets": wickets,
            "economy": economy
        })

    return sorted(performances, key=lambda x: (-x["wickets"], x["economy"]))


def calculate_player_score(batting_perf, bowling_perf, won_match=False, team_total_runs=0, fielding=None):
    """
    Calculate MVP points using the official Play-Cricket MVP formula.
    BATTING + BOWLING + FIELDING + CAPTAINCY + WINNING = TOTAL MVP
    """
    score = 0

    # BATTING
    if batting_perf:
        runs = batting_perf["runs"]
        # Every 20 runs (1pt)
        score += runs // 20
        # Reaching 50 (1pt)
        if runs >= 50:
            score += 1
        # Reaching 100 (1pt)
        if runs >= 100:
            score += 1
        # Scoring over 20% of team's runs (1pt)
        if team_total_runs > 0 and runs > (team_total_runs * 0.20):
            score += 1
        # Hitting 8 or more boundaries (1pt)
        boundaries = batting_perf["fours"] + batting_perf["sixes"]
        if boundaries >= 8:
            score += 1

    # BOWLING
    if bowling_perf:
        wickets = bowling_perf["wickets"]
        economy = bowling_perf["economy"]
        maidens = bowling_perf["maidens"]
        # Each wicket (1pt)
        score += wickets
        # Bonus for 3 wickets (1pt)
        if wickets >= 3:
            score += 1
        # Bonus for 5 wickets (1pt)
        if wickets >= 5:
            score += 1
        # Bowling 2 maidens (1pt)
        if maidens >= 2:
            score += 1
        # Achieving benchmark economy rate of 3.0 (1pt)
        if economy <= 3.0 and bowling_perf["overs"] not in ("0", ""):
            score += 1

    # FIELDING
    if fielding:
        catches = fielding.get("catches", 0)
        run_outs = fielding.get("run_outs", 0)
        stumpings = fielding.get("stumpings", 0)
        # Catches (1pt per)
        score += catches
        # Run outs (1pt per)
        score += run_outs
        # Stumpings (1pt per)
        score += stumpings
        # Bonus for 3 or more fielding dismissals in an innings (1pt)
        total_dismissals = catches + run_outs + stumpings
        if total_dismissals >= 3:
            score += 1

    # CAPTAINCY - not available in API data

    # WINNING - all members of winning team receive 1 bonus point
    if won_match:
        score += 1

    return score


def analyse_match(match_detail):
    """Analyse a single match and return top performers."""
    match = match_detail.get("match_details", [{}])[0] if "match_details" in match_detail else match_detail

    result_desc = match.get("result_description", "")
    result = match.get("result", "")

    if result == "A":  # Abandoned
        return None

    home_club = match.get("home_club_name", "")
    away_club = match.get("away_club_name", "")
    home_team_id = match.get("home_team_id", "")
    away_team_id = match.get("away_team_id", "")

    # Determine winning team from result description
    winning_team = ""
    if "Won" in result_desc:
        # result_description format: "Team Name - 1st XI - Won"
        winning_team = result_desc.split(" - ")[0].strip() if " - " in result_desc else ""

    innings_list = match.get("innings", [])
    if len(innings_list) < 2:
        return None

    # Collect all player performances across both innings
    player_performances = {}
    team_totals = {}  # team_name -> total runs

    for innings in innings_list:
        team_batting_id = innings.get("team_batting_id", "")
        team_name = home_club if team_batting_id == home_team_id else away_club
        innings_total = int(innings.get("runs", 0) or 0)
        team_totals[team_name] = team_totals.get(team_name, 0) + innings_total

        # Batting
        for bat in analyse_batting(innings):
            pid = bat["id"] or bat["name"]
            if pid not in player_performances:
                player_performances[pid] = {
                    "name": bat["name"],
                    "batting": None,
                    "bowling": None,
                    "fielding": {"catches": 0, "run_outs": 0, "stumpings": 0},
                    "team": team_name
                }
            # Keep best batting performance
            if player_performances[pid]["batting"] is None or bat["runs"] > player_performances[pid]["batting"]["runs"]:
                player_performances[pid]["batting"] = bat

        # Bowling (bowlers are on the fielding team, not the batting team)
        bowling_team = away_club if team_batting_id == home_team_id else home_club
        for bowl in analyse_bowling(innings):
            pid = bowl["id"] or bowl["name"]
            if pid not in player_performances:
                player_performances[pid] = {
                    "name": bowl["name"],
                    "batting": None,
                    "bowling": None,
                    "fielding": {"catches": 0, "run_outs": 0, "stumpings": 0},
                    "team": bowling_team
                }
            # Keep best bowling performance
            if player_performances[pid]["bowling"] is None or bowl["wickets"] > player_performances[pid]["bowling"]["wickets"]:
                player_performances[pid]["bowling"] = bowl

        # Fielding - extract from batting dismissals
        for bat in innings.get("bat", []):
            how_out = bat.get("how_out", "").lower()
            fielder_name = bat.get("fielder_name", "").strip()
            fielder_id = bat.get("fielder_id", "").strip()
            if not fielder_name or fielder_name.lower() == "unsure":
                continue
            # The fielder is on the bowling/fielding team
            fielding_team = away_club if team_batting_id == home_team_id else home_club
            fid = fielder_id or fielder_name
            if fid not in player_performances:
                player_performances[fid] = {
                    "name": fielder_name,
                    "batting": None,
                    "bowling": None,
                    "fielding": {"catches": 0, "run_outs": 0, "stumpings": 0},
                    "team": fielding_team
                }
            if "ct" in how_out:
                player_performances[fid]["fielding"]["catches"] += 1
            elif "run out" in how_out:
                player_performances[fid]["fielding"]["run_outs"] += 1
            elif "st" in how_out:
                player_performances[fid]["fielding"]["stumpings"] += 1

    # Score each player
    scored_players = []
    for pid, perf in player_performances.items():
        player_won = winning_team and winning_team in perf["team"]
        team_total = team_totals.get(perf["team"], 0)
        score = calculate_player_score(
            perf["batting"], perf["bowling"],
            won_match=player_won,
            team_total_runs=team_total,
            fielding=perf.get("fielding")
        )
        scored_players.append({
            "name": perf["name"],
            "team": perf["team"],
            "batting": perf["batting"],
            "bowling": perf["bowling"],
            "fielding": perf.get("fielding"),
            "score": score,
            "won_match": bool(player_won)
        })

    # Sort by score descending, then winning team first as tiebreaker
    scored_players.sort(key=lambda x: (x["score"], x["won_match"]), reverse=True)

    return {
        "match_id": match.get("match_id", ""),
        "home_club": home_club,
        "away_club": away_club,
        "result": result_desc,
        "winning_team": winning_team,
        "innings": innings_list,
        "top_performers": scored_players[:5]
    }


def format_performance(player):
    """Format a player's performance as a readable string."""
    parts = []
    if player["batting"] and player["batting"]["runs"] > 0:
        bat = player["batting"]
        no = "*" if bat["not_out"] else ""
        parts.append(f"{bat['runs']}{no} ({bat['balls']}b, {bat['fours']}x4, {bat['sixes']}x6)")
    if player["bowling"] and player["bowling"]["wickets"] > 0:
        bowl = player["bowling"]
        parts.append(f"{bowl['wickets']}/{bowl['runs']} ({bowl['overs']} ov, {bowl['maidens']}M)")
    if player.get("fielding"):
        f = player["fielding"]
        fielding_parts = []
        if f.get("catches", 0) > 0:
            fielding_parts.append(f"{f['catches']}ct")
        if f.get("run_outs", 0) > 0:
            fielding_parts.append(f"{f['run_outs']}ro")
        if f.get("stumpings", 0) > 0:
            fielding_parts.append(f"{f['stumpings']}st")
        if fielding_parts:
            parts.append(", ".join(fielding_parts))
    return " + ".join(parts) if parts else "N/A"


def generate_one_liner(player, won_match=False):
    """Generate a contextual one-liner description of a player's performance."""
    bat = player.get("batting")
    bowl = player.get("bowling")
    fielding = player.get("fielding")

    has_runs = bat and bat["runs"] > 0
    has_wickets = bowl and bowl["wickets"] > 0
    runs = bat["runs"] if has_runs else 0
    wickets = bowl["wickets"] if has_wickets else 0

    # All-rounder performances
    if has_runs and runs >= 30 and has_wickets and wickets >= 3:
        if wickets >= 5:
            return f"Superb all-round display — {wickets}-wicket haul and valuable {runs} runs"
        return f"Complete all-round performance with bat and ball"

    # Batting dominant
    if has_runs and runs >= 100:
        if won_match:
            return f"Match-winning century, commanding knock with {bat['fours'] + bat['sixes']} boundaries"
        return f"Brilliant century, {bat['fours'] + bat['sixes']} boundaries in a top-class innings"
    if has_runs and runs >= 75:
        sr = bat.get("strike_rate", 0)
        if sr > 150:
            return f"Explosive {runs} off just {bat['balls']} balls, blew the game open"
        if won_match:
            return f"Classy {runs} anchoring the innings, led team to victory"
        return f"Outstanding {runs} — nearly pulled it off for his side"
    if has_runs and runs >= 50:
        sr = bat.get("strike_rate", 0)
        if sr > 150:
            return f"Quick-fire fifty off {bat['balls']} balls with {bat['sixes']} sixes"
        return f"Solid half-century, backbone of the innings"

    # Bowling dominant
    if has_wickets and wickets >= 7:
        return f"Sensational {wickets}-wicket haul bowled his side to victory"
    if has_wickets and wickets >= 6:
        economy = bowl.get("economy", 99)
        if economy < 4.0:
            return f"Devastating {wickets}-wicket haul at under 4 an over, dismantled the batting"
        return f"Outstanding {wickets}-wicket haul ripped through the opposition"
    if has_wickets and wickets >= 5:
        maidens = bowl.get("maidens", 0)
        if maidens >= 3:
            return f"Brilliant {wickets}-wicket haul with {maidens} maidens, miserly and lethal"
        return f"Excellent {wickets}-wicket haul broke the back of the innings"
    if has_wickets and wickets >= 4:
        return f"Key {wickets}-wicket burst kept his side in control"

    # Fielding standout
    if fielding:
        total_f = fielding.get("catches", 0) + fielding.get("run_outs", 0) + fielding.get("stumpings", 0)
        if total_f >= 3:
            return f"Outstanding in the field with {total_f} dismissals"

    # Generic fallback
    if has_runs and has_wickets:
        return f"Handy contributions with both bat and ball"
    if has_runs:
        return f"Important knock of {runs} for his team"
    if has_wickets:
        return f"Picked up {wickets} key wickets"
    return "Solid all-round contribution"


def generate_whatsapp_summary(group_name, match_analyses):
    """Generate a WhatsApp-ready summary with one-liners for each match POTM."""
    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"📱 {group_name} — POTM Nominations (WhatsApp Ready)")
    lines.append(f"{'='*50}\n")

    overall_top = []
    match_num = 0

    for i, analysis in enumerate(match_analyses, 1):
        if analysis is None:
            continue

        if not analysis["top_performers"]:
            continue

        match_num += 1
        winner = analysis["top_performers"][0]
        # Determine opponent
        if winner["team"] == analysis["home_club"]:
            opponent = analysis["away_club"]
        else:
            opponent = analysis["home_club"]

        won_match = analysis.get("winning_team", "") and analysis["winning_team"] in winner["team"]
        one_liner = generate_one_liner(winner, won_match=won_match)
        perf_str = format_performance(winner)
        win_emoji = "✅" if won_match else "❌"

        # Determine result text
        result_text = analysis.get("result", "")

        lines.append(f"{match_num}. *{winner['name']}* ({winner['team']} {win_emoji}) vs {opponent}")
        lines.append(f"   Result: {result_text}")
        lines.append(f"   {perf_str} | {winner['score']:.0f}pts")
        lines.append(f"   _{one_liner}_")
        lines.append("")

        overall_top.append({
            **winner,
            "opponent": opponent,
            "won_match": won_match
        })

    # Overall pick — sort by score, then winning team as tiebreaker
    overall_top.sort(key=lambda x: (x["score"], x["won_match"]), reverse=True)
    if overall_top:
        pick = overall_top[0]
        one_liner = generate_one_liner(pick, won_match=pick["won_match"])
        perf_str = format_performance(pick)
        pick_emoji = "✅" if pick["won_match"] else "❌"
        lines.append(f"🏆 *{group_name} POTM: {pick['name']}* ({pick['team']} {pick_emoji}) vs {pick['opponent']}")
        lines.append(f"   {perf_str} | {pick['score']:.0f}pts")
        lines.append(f"   _{one_liner}_")

    return "\n".join(lines)


def get_team_abbrev(team_name):
    """Get short abbreviation for a team name."""
    if team_name in TEAM_ABBREVIATIONS:
        return TEAM_ABBREVIATIONS[team_name]
    # Fallback: first 2 letters of first word
    words = team_name.replace(" CC", "").split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][:2].upper()


def get_short_name(full_name):
    """Convert full name to initial + surname. e.g. 'Syed Imran' -> 'S Imran'"""
    parts = full_name.strip().split()
    if len(parts) <= 1:
        return full_name
    return f"{parts[0][0]} {parts[-1]}"


def format_performance_short(player):
    """Format performance in short form for poll options."""
    parts = []
    if player["batting"] and player["batting"]["runs"] > 0:
        bat = player["batting"]
        no = "*" if bat["not_out"] else ""
        parts.append(f"{bat['runs']}{no}({bat['balls']}b)")
    if player["bowling"] and player["bowling"]["wickets"] > 0:
        bowl = player["bowling"]
        parts.append(f"{bowl['wickets']}/{bowl['runs']}")
    if player.get("fielding"):
        f = player["fielding"]
        total = f.get("catches", 0) + f.get("run_outs", 0) + f.get("stumpings", 0)
        if total > 0:
            parts.append(f"{total}ct")
    return " & ".join(parts) if parts else "N/A"


def get_team_short(team_name):
    """Get team name without 'CC' suffix for poll options."""
    return team_name.replace(" CC", "").strip()


def generate_poll_options(group_name, match_analyses):
    """Generate WhatsApp poll options (max 100 chars each).
    Includes all top performers within 2 points of the highest scorer across all matches.
    Guarantees a minimum of 3 options for comparison.
    """
    lines = []
    lines.append(f"\n{'='*50}")
    lines.append(f"🗳️ {group_name} — WhatsApp Poll Options (max 100 chars)")
    lines.append(f"{'='*50}\n")

    # Collect ALL top performers from all matches with their match context
    all_candidates = []
    for analysis in match_analyses:
        if analysis is None:
            continue
        if not analysis["top_performers"]:
            continue

        for player in analysis["top_performers"]:
            # Determine opponent
            if player["team"] == analysis["home_club"]:
                opponent = analysis["away_club"]
            else:
                opponent = analysis["home_club"]

            all_candidates.append({
                "player": player,
                "opponent": opponent
            })

    if not all_candidates:
        lines.append("No candidates found.")
        return "\n".join(lines)

    # Sort by score descending, then winning team as tiebreaker
    all_candidates.sort(key=lambda c: (c["player"]["score"], c["player"].get("won_match", False)), reverse=True)

    # Remove duplicates (same player appearing in multiple contexts) - keep highest score
    seen = set()
    unique_candidates = []
    for c in all_candidates:
        name = c["player"]["name"]
        if name not in seen:
            seen.add(name)
            unique_candidates.append(c)

    # Find the top score and determine poll options
    top_score = unique_candidates[0]["player"]["score"]
    second_score = unique_candidates[1]["player"]["score"] if len(unique_candidates) > 1 else 0

    # If the leader is 3+ points clear, they're a clear winner — show only top 3
    if top_score - second_score >= 3:
        filtered = unique_candidates[:3]
    else:
        # Otherwise show all within 2 points of the top, capped at 5
        threshold = top_score - 2
        filtered = [c for c in unique_candidates if c["player"]["score"] >= threshold]
        if len(filtered) > 5:
            filtered = filtered[:5]

    # Ensure minimum 3 options for comparison
    if len(filtered) < 3 and len(unique_candidates) >= 3:
        filtered = unique_candidates[:3]
    elif len(filtered) < 3:
        filtered = unique_candidates

    for i, candidate in enumerate(filtered, 1):
        winner = candidate["player"]
        opponent = candidate["opponent"]
        short_name = get_short_name(winner["name"])
        team_short = get_team_short(winner["team"])
        opp_short = get_team_short(opponent)
        win_emoji = "✅" if winner.get("won_match", False) else "❌"

        perf = format_performance_short(winner)
        poll_option = f"{short_name} ({team_short} {win_emoji}) vs {opp_short} - {perf}"

        # Ensure under 100 chars
        if len(poll_option) > 100:
            poll_option = poll_option[:97] + "..."

        lines.append(poll_option)

    return "\n".join(lines)


def generate_report(group_name, match_analyses):
    """Generate a formatted report for a group."""
    lines = []
    lines.append(f"\n## {group_name} — Player of the Match Contenders\n")

    all_top_performers = []

    for i, analysis in enumerate(match_analyses, 1):
        if analysis is None:
            lines.append(f"### Match {i}: Abandoned/No data\n")
            continue

        lines.append(f"### Match {i}: {analysis['home_club']} vs {analysis['away_club']}")
        lines.append(f"**Result:** {analysis['result']}\n")

        lines.append("| Rank | Player | Team | Performance | Score |")
        lines.append("|------|--------|------|-------------|-------|")

        for j, player in enumerate(analysis["top_performers"][:3], 1):
            perf_str = format_performance(player)
            lines.append(f"| {j} | {player['name']} | {player['team']} | {perf_str} | {player['score']:.0f} |")
            all_top_performers.append(player)

        lines.append("")

    # Overall POTM recommendation — sort by score, then winning team as tiebreaker
    all_top_performers.sort(key=lambda x: (x["score"], x.get("won_match", False)), reverse=True)
    if all_top_performers:
        lines.append(f"### 🏆 {group_name} — Overall POTM Recommendation\n")
        lines.append("| Rank | Player | Team | Performance | Score |")
        lines.append("|------|--------|------|-------------|-------|")
        for j, player in enumerate(all_top_performers[:5], 1):
            perf_str = format_performance(player)
            lines.append(f"| {j} | **{player['name']}** | {player['team']} | {perf_str} | {player['score']:.0f} |")
        lines.append("")
        winner = all_top_performers[0]
        lines.append(f"**My pick: {winner['name']} ({winner['team']})** — {format_performance(winner)}")

    return "\n".join(lines)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Play Cricket POTM Analyser")
    parser.add_argument("--date", help="Match date in DD/MM/YYYY format (default: last Saturday)")
    parser.add_argument("--group", choices=["A", "B", "both", "sjr", "broadbent", "cup", "t20", "all"], default="all",
                        help="Which competition to analyse: A, B, both (league only), sjr, broadbent, cup (all Saturday cups), t20 (Tuesday T20), all (everything)")
    args = parser.parse_args()

    # Use last Tuesday for T20, last Saturday for everything else
    if args.group == "t20":
        match_date = args.date or get_last_tuesday()
    else:
        match_date = args.date or get_last_saturday()
    print(f"Fetching matches for date: {match_date}")
    print(f"Season: {SEASON}, Site ID: {SITE_ID}\n")

    # Fetch match list
    matches = fetch_matches(match_date)
    print(f"Found {len(matches)} matches on {match_date}\n")

    if not matches:
        print("No matches found. Try specifying a different date with --date DD/MM/YYYY")
        return

    # Categorize
    group_a, group_b, sjr_cup_a, sjr_cup_b, broadbent_a, broadbent_b, t20_group_a, t20_group_b, t20_group_c = categorize_matches(matches)
    print(f"Group A: {len(group_a)} matches")
    print(f"Group B: {len(group_b)} matches")
    print(f"SJR Cup Pool A: {len(sjr_cup_a)} matches")
    print(f"SJR Cup Pool B: {len(sjr_cup_b)} matches")
    print(f"H. Broadbent Trophy Pool A: {len(broadbent_a)} matches")
    print(f"H. Broadbent Trophy Pool B: {len(broadbent_b)} matches")
    print(f"Rizues T20 Group A: {len(t20_group_a)} matches")
    print(f"Rizues T20 Group B: {len(t20_group_b)} matches")
    print(f"Rizues T20 Group C: {len(t20_group_c)} matches\n")

    # Define which competitions to process based on --group arg
    competitions_to_process = []

    if args.group in ("A", "both", "all"):
        if group_a:
            competitions_to_process.append(("Group A", group_a))
    if args.group in ("B", "both", "all"):
        if group_b:
            competitions_to_process.append(("Group B", group_b))
    if args.group in ("sjr", "cup", "all"):
        # Combine SJR Cup Pool A & B into a single competition
        sjr_combined = sjr_cup_a + sjr_cup_b
        if sjr_combined:
            competitions_to_process.append(("SJR Cup", sjr_combined))
    if args.group in ("broadbent", "cup", "all"):
        # Combine H. Broadbent Trophy Pool A & B into a single competition
        broadbent_combined = broadbent_a + broadbent_b
        if broadbent_combined:
            competitions_to_process.append(("H. Broadbent Trophy", broadbent_combined))
    if args.group in ("t20", "all"):
        if t20_group_a:
            competitions_to_process.append(("Rizues T20 Group A", t20_group_a))
        if t20_group_b:
            competitions_to_process.append(("Rizues T20 Group B", t20_group_b))
        if t20_group_c:
            competitions_to_process.append(("Rizues T20 Group C", t20_group_c))

    if not competitions_to_process:
        print("No matches found for the selected competition(s).")
        return

    # Fetch and analyse each competition
    all_analyses = {}  # comp_name -> list of analyses

    for comp_name, comp_matches in competitions_to_process:
        print(f"Fetching {comp_name} match details...")
        analyses = []
        for match in comp_matches:
            mid = match.get("id") or match.get("match_id")
            detail = fetch_match_detail(mid)
            analysis = analyse_match(detail)
            analyses.append(analysis)
        all_analyses[comp_name] = analyses
        print(generate_report(comp_name, analyses))

    # WhatsApp-ready summary
    print("\n\n" + "=" * 60)
    print("📱 WHATSAPP-READY SUMMARY")
    print("=" * 60)

    for comp_name, analyses in all_analyses.items():
        if analyses:
            print(generate_whatsapp_summary(comp_name, analyses))

    # WhatsApp poll options (short form, max 100 chars)
    print("\n\n" + "=" * 60)
    print("🗳️ WHATSAPP POLL OPTIONS")
    print("=" * 60)

    for comp_name, analyses in all_analyses.items():
        if analyses:
            print(generate_poll_options(comp_name, analyses))


if __name__ == "__main__":
    main()
