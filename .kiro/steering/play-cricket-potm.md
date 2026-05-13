---
inclusion: manual
---

# Play Cricket — Player of the Match Analysis

## Overview
This workflow fetches match data from the Play Cricket API and analyses both innings (batting + bowling) across all matches in Group A and Group B to recommend Player of the Match.

## Configuration
- **API Base:** http://play-cricket.com/api/v2/
- **Site ID:** 262 (Bradford Mutual Sunday School Cricket League)
- **Season:** Current year
- **Group A Competition ID:** 136363
- **Group B Competition ID:** 137864
- **Match Day:** Saturday (default: last Saturday from when invoked)

## How to Run

Run the script at `.kiro/scripts/play_cricket_mcp.py`:

```bash
python .kiro/scripts/play_cricket_mcp.py --group both
```

Or for a specific date:
```bash
python .kiro/scripts/play_cricket_mcp.py --date 25/04/2026 --group A
```

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

For each group, produce:
- Per-match breakdown with top 3 performers
- Overall group POTM ranking (top 5)
- Final recommendation with reasoning

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
