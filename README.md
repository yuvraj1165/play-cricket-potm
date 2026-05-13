# Play Cricket � POTM Analyser

Automated Player of the Match analysis for Bradford Mutual Sunday School Cricket League.

## Setup

1. Set your API token as an environment variable:
   ```
   set PLAY_CRICKET_API_TOKEN=your_api_key_here
   ```

2. Open this folder as a workspace in Kiro

3. Click the "Play Cricket POTM" hook button, or run manually:
   ```
   python .kiro/scripts/play_cricket_mcp.py --group both
   ```

## Usage

- **Default:** Analyses last Saturday's matches for both groups
- **Specific date:** `python .kiro/scripts/play_cricket_mcp.py --date 25/04/2026`
- **Single group:** `python .kiro/scripts/play_cricket_mcp.py --group A`

## Configuration

- Site ID: 262 (BMSSCL)
- Group A: Competition 136363
- Group B: Competition 137864
- Season: Auto-detected (current year)
