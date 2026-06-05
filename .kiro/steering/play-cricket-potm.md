---
inclusion: manual
---

# Play Cricket — Player of the Match Analysis

## Overview
This workflow fetches match data from the Play Cricket API and analyses performances across all competitions to recommend Player of the Match.

## Configuration
- **API Base:** https://www.play-cricket.com/api/v2/
- **Site ID:** 262 (Bradford Mutual Sunday School Cricket League)
- **Season:** Current year

### League Competitions (Saturdays)
- **Group A Competition ID:** 136363
- **Group B Competition ID:** 137864

### Cup Competitions (Saturdays)
- **SJR Cup Pool A ID:** 137059
- **SJR Cup Pool B ID:** 137060
- **H. Broadbent Trophy Pool A ID:** 137061
- **H. Broadbent Trophy Pool B ID:** 137062

### T20 Competitions (Tuesdays)
- **Rizues T20 Group A ID:** 138140
- **Rizues T20 Group B ID:** 138141
- **Rizues T20 Group C ID:** 138142

## How to Run

Run the script at `.kiro/scripts/play_cricket_mcp.py`:

```bash
# League matches (last Saturday)
python .kiro/scripts/play_cricket_mcp.py --group both

# All Saturday competitions (league + cups)
python .kiro/scripts/play_cricket_mcp.py --group all

# Cup matches only
python .kiro/scripts/play_cricket_mcp.py --group cup

# SJR Cup only
python .kiro/scripts/play_cricket_mcp.py --group sjr

# H. Broadbent Trophy only
python .kiro/scripts/play_cricket_mcp.py --group broadbent

# T20 matches (auto-detects last Tuesday)
python .kiro/scripts/play_cricket_mcp.py --group t20

# Specific date
python .kiro/scripts/play_cricket_mcp.py --date 25/04/2026 --group A
```

### Available --group options
| Option | Description | Default date |
|--------|-------------|--------------|
| A | League Group A only | Last Saturday |
| B | League Group B only | Last Saturday |
| both | League Group A + B | Last Saturday |
| sjr | SJR Cup (Pool A + B combined) | Last Saturday |
| broadbent | H. Broadbent Trophy (Pool A + B combined) | Last Saturday |
| cup | All cup matches (SJR + Broadbent) | Last Saturday |
| t20 | Rizues T20 (Groups A, B, C separate) | Last Tuesday |
| all | Everything available on that date | Last Saturday |

## Environment Variable Required
Set `PLAY_CRICKET_API_TOKEN` with your Play Cricket API key before running.

## Analysis Criteria

When selecting Player of the Match, consider:

1. **Match-winning contribution** — Did the performance directly win the game?
2. **Context** — Coming in at 70/6 and scoring 80* is more impressive than 80 at 200/2
3. **All-round performances** — Bat + bowl contributions get extra weight
4. **Bowling economy + wickets** — 6/4 is better than 6/50
5. **Strike rate in context** — High SR in a chase is more valuable than in a dead rubber
6. **Winning team preference** — All else being equal, prefer the winner's player

## Output Format

For each competition, produce:
- Per-match breakdown with top 3 performers (one nominee per match)
- Overall POTM ranking (top 5)
- Final recommendation with reasoning
- WhatsApp-ready summary with one-liners
- WhatsApp poll options (max 100 chars each, ✅/❌ for win/loss)

## Tiebreaker Rules
- Primary: Score (descending)
- Secondary: Winning team player ranks above losing team player at same score

## Poll Options Logic
- If leader is 3+ points clear: show top 3 only
- Otherwise: show all within 2 points of top, max 5
- Minimum 3 options always shown

## Scoring Weights (Play-Cricket MVP Formula)

**BATTING + BOWLING + FIELDING + CAPTAINCY + WINNING = TOTAL MVP**

### Batting
- Every 20 runs: +1pt
- Reaching 50: +1pt
- Reaching 100: +1pt
- Scoring over 20% of team's runs: +1pt
- Hitting 8 or more boundaries: +1pt

### Bowling
- Each wicket: +1pt
- Bonus for 3 wickets in an innings: +1pt
- Bonus for 5 wickets in an innings: +1pt
- Bowling 2 maidens: +1pt
- Achieving economy rate of 3.0 or below: +1pt

### Fielding
- Catches: +1pt per
- Run outs: +1pt per
- Stumpings: +1pt per
- Bonus for 3+ fielding dismissals in an innings: +1pt

### Captaincy
- Captain of winning side: +1pt (not available via API)

### Winning
- All members of winning team: +1pt

## Competition Grouping
- **SJR Cup**: Pool A + Pool B combined into single POTM
- **H. Broadbent Trophy**: Pool A + Pool B combined into single POTM
- **Rizues T20**: Groups A, B, C kept separate with individual POTM per group

## Player Insights Script

A separate script at `.kiro/scripts/player_insights.py` can analyse individual player performance across all matches in a season:

```bash
python .kiro/scripts/player_insights.py <player_id>
```

Returns batting average, strike rate, bowling figures, fielding stats, and match-by-match breakdown.
