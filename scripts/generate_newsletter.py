#!/usr/bin/env python3
"""Generates today's newsletter.json using Claude API with web search."""

import anthropic
import json
import os
import sys
from datetime import datetime, timezone

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")

    print(f"Generating newsletter for {today}...")

    news_prompt = f"""Today is {today}. You are the editor of The Daily Edition, a newspaper for curious readers aged 10–20.

Your job: use web search to find real stories from TODAY or the past 48 hours. Avoid politics and violence. Be accurate — no making things up.

Write TWO sets of articles:

SET 1 — "featured" (3 articles): Pick the 3 most surprising, funny, or interesting stories of the day. Any topic mix is fine.

SET 2 — "articles" (7 articles): Exactly one story per section using these exact section names:
1. WORLD — a surprising or unexpected story from somewhere on the globe
2. SPACE — something from astronomy, NASA, rockets, or the cosmos
3. SCIENCE — a discovery, study, or breakthrough in any field of science
4. NATURE — wildlife, animals, environment, conservation, or weather
5. TECH — AI, gadgets, internet, software, robots, or digital culture
6. CULTURE — art, music, film, food, fashion, history, or human stories
7. ANIMALS — a specific animal story (weird creature, rescue, new species, behavior)

For each story write a FULL article with at least 4 paragraphs. Use a dateline (CITY — ...) to open the first paragraph. Engaging newspaper style for a 14-year-old.

Return ONLY a JSON object with this exact shape (no markdown, no extra text):
{{
  "date": "{today}",
  "edition": 3,
  "featured": [
    {{
      "section": "SECTION NAME",
      "headline": "Headline Here",
      "subheadline": "A one-sentence summary.",
      "body": "Full article. Double newlines (\\n\\n) between paragraphs."
    }}
  ],
  "articles": [
    {{
      "section": "WORLD",
      "headline": "Headline Here",
      "subheadline": "A one-sentence summary.",
      "body": "Full article. Double newlines (\\n\\n) between paragraphs."
    }}
  ],
  "games": [
    {{ "name": "The Lying Museum", "emoji": "🕵️", "desc": "Find the one fake fact hidden inside 5 museum exhibits.", "file": "lying-museum.html", "accent": "#f5a623" }},
    {{ "name": "Time Capsule", "emoji": "⏳", "desc": "A mystery object with no date. Guess which decade it came from.", "file": "time-capsule.html", "accent": "#00c9a7" }},
    {{ "name": "Species or Fiction", "emoji": "🧬", "desc": "Real bizarre animals vs. completely invented ones. Can you tell?", "file": "species-or-fiction.html", "accent": "#2dd60f" }},
    {{ "name": "Escape the Island", "emoji": "🗺️", "desc": "5 locations, 5 puzzles, 3 energy bars. Solve them all.", "file": "escape-the-island.html", "accent": "#ff6b35" }},
    {{ "name": "Two Truths and a Twist", "emoji": "🎭", "desc": "Find the lie — then fix it. Half points for spotting, full for correcting.", "file": "two-truths-and-a-twist.html", "accent": "#9b5de5" }},
    {{ "name": "Chain Gang", "emoji": "🔗", "desc": "Word chain where the connection rule changes every round.", "file": "chain-gang.html", "accent": "#00f5ff" }}
  ]
}}"""

    sports_prompt = f"""Today is {today}. Search the web for real, current sports data across: MLS Soccer, NBA, NFL, MLB, NHL, and ATP/WTA Tennis.

For EACH sport return:
1. Today's scores/results (finished games) and tonight's upcoming schedule with tip-off times
2. Current league standings — top 5 teams per conference/division (wins, losses, draws if applicable, points or win%)
3. Top 5 players right now — name, team, their key stat and value (goals, PPG, HR, etc.)

If a sport is currently off-season (no active season), set "inSeason": false and leave games/standings/topPlayers as empty arrays.

Use short team names (e.g. "Lakers" not "Los Angeles Lakers"). For tennis standings, list top 5 ranked players instead of teams.

Return ONLY a JSON array, no markdown, no extra text:
[
  {{
    "sport": "League Name (e.g. MLS Soccer)",
    "slug": "soccer",
    "emoji": "⚽",
    "inSeason": true,
    "games": [
      {{"away": "Team", "home": "Team", "awayScore": 2, "homeScore": 1, "status": "Final"}},
      {{"away": "Team", "home": "Team", "awayScore": null, "homeScore": null, "status": "7:30 PM ET"}}
    ],
    "standings": [
      {{"rank": 1, "team": "Team Name", "conference": "Eastern", "played": 20, "wins": 14, "draws": 3, "losses": 3, "pts": 45, "ptsLabel": "Pts"}}
    ],
    "topPlayers": [
      {{"name": "Player Name", "team": "Team", "stat": "Goals", "value": "18"}}
    ]
  }}
]

Always include all 6 sports even if off-season (use inSeason: false). Slugs must be one of: soccer, football, basketball, baseball, hockey, tennis."""

    # Generate news articles
    print("Fetching news articles...")
    news_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
        messages=[{"role": "user", "content": news_prompt}]
    )

    # Generate sports scores
    print("Fetching sports scores...")
    sports_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": sports_prompt}]
    )

    def extract_json(response):
        for block in response.content:
            if block.type != "text":
                continue
            text = block.text.strip()
            # Try extracting from code fence anywhere in the text
            if "```" in text:
                parts = text.split("```")
                for part in parts[1::2]:  # every other part is inside fences
                    if part.startswith("json"):
                        part = part[4:]
                    try:
                        return json.loads(part.strip())
                    except json.JSONDecodeError:
                        continue
            # Try raw JSON (find first { or [)
            for start_char, end_char in [('{', '}'), ('[', ']')]:
                idx = text.find(start_char)
                if idx != -1:
                    try:
                        return json.loads(text[idx:])
                    except json.JSONDecodeError:
                        pass
        return None

    newsletter_json = extract_json(news_response)
    if not newsletter_json:
        print("ERROR: Could not parse newsletter JSON")
        sys.exit(1)

    sports_json = extract_json(sports_response)
    if sports_json and isinstance(sports_json, list):
        newsletter_json["sports"] = sports_json
        print(f"Sports: {len(sports_json)} leagues loaded")
    else:
        newsletter_json["sports"] = []
        print("Sports: no data available today")

    docs = os.path.join(os.path.dirname(__file__), "..", "docs")

    with open(os.path.join(docs, "newsletter.json"), "w") as f:
        json.dump(newsletter_json, f, indent=2, ensure_ascii=False)

    iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_dir = os.path.join(docs, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    with open(os.path.join(archive_dir, f"{iso}.json"), "w") as f:
        json.dump(newsletter_json, f, indent=2, ensure_ascii=False)

    index_path = os.path.join(archive_dir, "index.json")
    index = []
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    index = [e for e in index if e.get("isoDate") != iso]
    entry = {
        "date": newsletter_json["date"],
        "isoDate": iso,
        "articles": [
            {"section": a["section"], "headline": a["headline"],
             "subheadline": a["subheadline"], "body": a["body"]}
            for a in newsletter_json["articles"]
        ]
    }
    index.insert(0, entry)
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"Done! {len(newsletter_json['articles'])} articles + {len(newsletter_json['sports'])} sport leagues.")

if __name__ == "__main__":
    main()
