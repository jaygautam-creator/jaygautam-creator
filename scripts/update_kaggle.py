"""Rewrite the Kaggle block in README.md (between the KAGGLE markers) from the Kaggle API.

Auth: KAGGLE_API_TOKEN env var (CI) or ~/.kaggle/access_token (local).
"""
import pathlib
import re
from datetime import datetime, timezone

from kaggle.api.kaggle_api_extended import KaggleApi

README = pathlib.Path(__file__).resolve().parent.parent / "README.md"

api = KaggleApi()
api.authenticate()
resp = api.competitions_list(group="entered")
comps = getattr(resp, "competitions", resp)

today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
rows = []
for c in comps:
    rank, teams = int(c.user_rank or 0), int(c.team_count or 0)
    if rank <= 0 or teams <= 0:
        continue
    slug = str(c.ref).rstrip("/").split("/")[-1]
    deadline = str(c.deadline)[:10]
    rows.append((rank / teams, c.title, slug, rank, teams, deadline))
rows.sort()

lines = ["| Competition | Rank | Standing | Status |", "|:--|--:|:-:|:--|"]
for frac, title, slug, rank, teams, deadline in rows:
    status = f"Live · ends {datetime.strptime(deadline, '%Y-%m-%d'):%d %b %Y}" if deadline >= today else "Final"
    lines.append(
        f"| **[{title}](https://www.kaggle.com/competitions/{slug})** | **#{rank:,}** of {teams:,} | Top {max(1, -(-rank * 100 // teams))}% | {status} |"
    )
lines.append("")
lines.append(f"<sub>Public-leaderboard ranks, refreshed daily from the Kaggle API · last updated {datetime.now(timezone.utc):%d %b %Y}</sub>")

block = "\n".join(lines)
text = README.read_text()
new = re.sub(
    r"<!-- KAGGLE:START -->.*?<!-- KAGGLE:END -->",
    lambda m: "<!-- KAGGLE:START -->\n" + block + "\n<!-- KAGGLE:END -->",
    text,
    flags=re.S,
)
README.write_text(new)
print(f"{len(rows)} competitions")
