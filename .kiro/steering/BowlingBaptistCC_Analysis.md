---
inclusion: manual
---

# Bowling Baptist CC — Season Analysis & NRR Optimisation

## Overview
This workflow analyses Bowling Baptist CC's match data from the Play Cricket API to provide overall season performance insights and guidance on how to improve Net Run Rate (NRR).

## Configuration
- **API Base:** https://www.play-cricket.com/api/v2/
- **Site ID:** 288 (Bowling Baptist CC)
- **Season:** Current year
- **Competition ID:** 138199

## How to Run

```bash
python .kiro/scripts/bowling_baptist_analysis.py
```

## Environment Variable Required
Set `PLAY_CRICKET_API_TOKEN` with your Play Cricket API key before running.

## Analysis Goals

### 1. Overall Season Performance
- Matches played, won, lost, drawn, abandoned
- Win percentage and form (last 5 matches)
- Batting and bowling averages across the season
- Key performers (top run scorers, top wicket takers)

### 2. Net Run Rate (NRR) Analysis
NRR = (Total runs scored / Total overs faced) - (Total runs conceded / Total overs bowled)

**To improve NRR, the team needs to:**
- **Score runs quickly** — higher run rate when batting
- **Bowl teams out cheaply and quickly** — lower run rate conceded
- **Win by big margins** — especially when batting first (bowl teams out fast) or chasing (win with overs to spare)

### 3. NRR Optimisation Insights
For each match, calculate:
- Run rate scored vs run rate conceded
- NRR contribution (positive or negative)
- Identify matches that hurt NRR most
- Suggest tactical adjustments:
  - When batting first: what target is needed to boost NRR
  - When chasing: how many overs to spare would improve NRR
  - When bowling: how quickly to dismiss opposition

### 4. Projected NRR Scenarios
- Current NRR
- NRR needed to reach a specific league position
- "What if" scenarios: if next match is won by X runs / Y overs

## Output Format
- Season summary table
- NRR breakdown per match
- Top performers
- NRR improvement recommendations
- Projected scenarios for upcoming matches

## NRR Formula Reference
```
NRR = (Runs scored / Overs faced) - (Runs conceded / Overs bowled)
```

For teams bowled out:
- Overs faced = full allocation (e.g. 40 overs if bowled out in 30)
- Overs bowled = actual overs bowled to dismiss them

For incomplete innings (rain, etc.):
- Use actual overs played
