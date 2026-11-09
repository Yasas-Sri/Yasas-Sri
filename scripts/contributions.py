"""Regenerate the open source contribution sections of README.md from the GitHub API.

Usage: GITHUB_TOKEN=... python scripts/contributions.py   (falls back to `gh auth token`)
       python scripts/contributions.py --test
"""
import json, os, re, subprocess, sys, textwrap, urllib.parse, urllib.request
from xml.sax.saxutils import escape
from collections import defaultdict

USER = "Yasas-Sri"
# ponytail: coursework/team repos aren't "open source contributions", edit this set to taste
EXCLUDE = {"ComputerScienceSJP/projects-team-8", "sofflix/hrm-web", "Sahan-Madusanka-Perera/gym-leveling-desktop"}
INLINE_LINKS = 3  # more merged PRs than this -> "View all" link
README = os.path.join(os.path.dirname(__file__), "..", "README.md")
GRAPH = os.path.join(os.path.dirname(__file__), "..", "contributions.svg")


def api(path):
    token = os.environ.get("GITHUB_TOKEN") or subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
    req = urllib.request.Request(f"https://api.github.com/{path}", headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def search_prs(state):
    q = urllib.parse.quote(f"is:pr {state} author:{USER} -user:{USER}")
    items, page = [], 1
    while True:
        batch = api(f"search/issues?q={q}&per_page=100&page={page}")["items"]
        items += batch
        if len(batch) < 100:
            return [i for i in items if repo_of(i) not in EXCLUDE]
        page += 1


def repo_of(pr):
    return pr["repository_url"].split("/repos/")[1]


def stars(n):
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def render(merged, open_count, info):
    """merged: {repo: [pr]}, info: {repo: (stars, branch, commits)} -> {section: markdown}"""
    repos = sorted(merged, key=lambda r: -info[r][0])
    total_stars = sum(info[r][0] for r in repos)
    n_prs = sum(len(v) for v in merged.values())
    summary = f"{n_prs} merged PRs in {len(repos)} projects, {open_count} more open."
    rows = ["| Repository | Stars | Commits | Merged PRs | PR Links |", "|:--|--:|:--:|:--:|:--|"]
    for r in repos:
        st, branch, commits = info[r]
        prs = sorted(merged[r], key=lambda p: p["number"])
        if len(prs) > INLINE_LINKS:
            links = f"[View all](https://github.com/{r}/pulls?q=is%3Apr+is%3Amerged+author%3A{USER})"
        else:
            links = ", ".join(f"[#{p['number']}]({p['html_url']})" for p in prs)
        rows.append(f"| [{r}](https://github.com/{r}) | {stars(st)} | "
                    f"[{commits}](https://github.com/{r}/commits/{branch}?author={USER}) | {len(prs)} | {links} |")
    return {"summary": summary, "contributions": "\n".join(rows)}


SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
BRANCH_COLORS = ["#a78bfa", "#f0b429", "#22d3ee", "#f472b6", "#3fb950", "#fb923c"]
LANG_COLORS = {"Python": "#3572A5", "Rust": "#dea584", "Go": "#00ADD8", "TypeScript": "#3178c6",
               "JavaScript": "#f1e05a", "C": "#555555", "C++": "#f34b7d", "Jupyter Notebook": "#DA5B0B"}


def clip(s, n):
    s = re.sub(r"[\U0001F000-\U0001FFFF\u2600-\u27BF\uFE0F]", "", s).replace("  ", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def render_svg(cards):
    """cards: [{title, sub, desc, badge, lang}] in commit order -> animated git-graph SVG."""
    W = max(1000, 60 + 110 * (len(cards) - 1) + 200)
    t = lambda x, y, s, size, fill, font=SANS, extra="": (
        f'<text x="{x}" y="{y}" {extra}font-family="{font}" font-size="{size}" fill="{fill}">{escape(s)}</text>')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="540" '
           f'viewBox="0 0 {W} 540" role="img" aria-label="Open-source contributions as a git graph">',
           '<defs><linearGradient id="main" x1="0" x2="1"><stop offset="0" stop-color="#a78bfa"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>'
           '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#ffffff" stroke-opacity=".035"/></pattern></defs>',
           '<style>.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1s ease forwards}@keyframes draw{to{stroke-dashoffset:0}}'
           '.pop{opacity:0;animation:pop .6s ease forwards}@keyframes pop{from{opacity:0;transform:translateY(var(--dy))}to{opacity:1;transform:none}}'
           '.commit{transform-box:fill-box;transform-origin:center;animation:beat 2.4s ease-in-out infinite}@keyframes beat{0%,100%{transform:scale(1)}50%{transform:scale(1.35)}}</style>',
           f'<rect width="{W}" height="540" rx="18" fill="#0d1117"/><rect width="{W}" height="540" rx="18" fill="url(#grid)"/>',
           f'<rect x=".5" y=".5" width="{W - 1}" height="539" rx="18" fill="none" stroke="#30363d"/>',
           f'<path class="draw" pathLength="1" d="M30 270 H{W - 30}" stroke="url(#main)" stroke-width="3" fill="none" stroke-linecap="round"/>',
           t(34, 292, f"{USER.split('-')[0].lower()}/main", 11, "#8b949e", MONO),
           t(W - 34, 292, "HEAD →", 11, "#22d3ee", MONO, 'text-anchor="end" '),
           f'<circle r="4.5" fill="#22d3ee"><animateMotion dur="7s" repeatCount="indefinite" path="M30 270 H{W - 30}"/>'
           '<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.05;.9;1" dur="7s" repeatCount="indefinite"/></circle>']
    for i, c in enumerate(cards):
        col, cx, top, d = BRANCH_COLORS[i % len(BRANCH_COLORS)], 60 + 110 * i, i % 2 == 0, 0.28 * i
        ax, ay, y = cx + 70, (150 if top else 390), (28 if top else 390)
        bend = (cx, 200, ax, 220) if top else (cx, 340, ax, 320)
        x = cx - 30
        out += [f'<path id="b{i}" class="draw" pathLength="1" style="animation-delay:{.7 + d:.2f}s" d="M{cx} 270 C{bend[0]} {bend[1]} {bend[2]} {bend[3]} {ax} {ay}" '
                f'stroke="{col}" stroke-opacity=".75" stroke-width="2.2" fill="none"/>',
                f'<circle class="commit" style="animation-delay:{d:.2f}s" cx="{cx}" cy="270" r="6" fill="#0d1117" stroke="{col}" stroke-width="2.5"/>',
                f'<circle r="3" fill="{col}" opacity="0"><animateMotion dur="2.6s" begin="{1.9 + d:.2f}s" repeatCount="indefinite"><mpath xlink:href="#b{i}"/></animateMotion>'
                f'<set attributeName="opacity" to="1" begin="{1.9 + d:.2f}s"/></circle>',
                f'<g class="pop" style="animation-delay:{1.3 + d:.2f}s;--dy:{10 if top else -10}px">',
                f'<rect x="{x}" y="{y}" width="200" height="122" rx="12" fill="#161b22" stroke="{col}" stroke-opacity=".45"/>',
                f'<rect x="{x + 14}" y="{y}" width="44" height="3" rx="1.5" fill="{col}"/><circle cx="{ax}" cy="{ay}" r="4" fill="{col}"/>',
                t(x + 14, y + 28, clip(c["title"], 20), 16, "#e6edf3", extra='font-weight="700" '),
                t(x + 14, y + 45, clip(c["sub"], 28), 10.5, "#8b949e", MONO)]
        lines = textwrap.wrap(c["desc"] or "", 27) or [""]
        if len(lines) > 2:
            lines = [lines[0], clip(lines[1] + " " + lines[2], 27)]
        out += [t(x + 14, y + 66 + 15 * k, line, 12, "#c9d1d9") for k, line in enumerate(lines)]
        bw = 16 + 6.6 * len(c["badge"])
        out += [f'<rect x="{x + 14}" y="{y + 93}" width="{bw:.1f}" height="20" rx="10" fill="{col}" fill-opacity=".14"/>',
                t(x + 22, y + 107, c["badge"], 11, col, MONO, 'font-weight="700" ')]
        if c["lang"]:
            out += [t(x + 186, y + 107, c["lang"], 11, "#8b949e", extra='text-anchor="end" '),
                    f'<circle cx="{x + 186 - 6.2 * len(c["lang"]) - 10:.1f}" cy="{y + 103}" r="4" fill="{LANG_COLORS.get(c["lang"], "#8b949e")}"/>']
        out.append("</g>")
    return "\n".join(out + ["</svg>"])


def card(repo, prs, meta):
    nums = sorted(p["number"] for p in prs)
    badge = "PR " + " · ".join(f"#{n}" for n in nums) if len(nums) <= 2 else f"{len(nums)} PRS MERGED"
    return {"title": repo.split("/")[1], "sub": repo, "desc": clip(meta.get("description") or "", 200), "badge": badge, "lang": meta.get("language")}


def splice(text, sections):
    for name, body in sections.items():
        text = re.sub(rf"(<!-- START_SECTION:{name} -->).*?(<!-- END_SECTION:{name} -->)",
                      lambda m: f"{m[1]}\n{body}\n{m[2]}", text, flags=re.S)
    return text


def main():
    merged = defaultdict(list)
    for pr in search_prs("is:closed"):  # search's is:merged filter misses some PRs; merged_at doesn't
        if pr["pull_request"].get("merged_at"):
            merged[repo_of(pr)].append(pr)
    info, metas = {}, {}
    for r in merged:
        meta = metas[r] = api(f"repos/{r}")
        # ponytail: caps at 100 commits per repo, paginate if you ever pass that
        commits = len(api(f"repos/{r}/commits?author={USER}&sha={meta['default_branch']}&per_page=100"))
        info[r] = (meta["stargazers_count"], meta["default_branch"], commits)
    first_merge = lambda r: min(p["pull_request"]["merged_at"] for p in merged[r])
    with open(GRAPH, "w") as f:  # oldest contribution on the left, like a git log
        f.write(render_svg([card(r, merged[r], metas[r]) for r in sorted(merged, key=first_merge)]))
    with open(README) as f:
        text = f.read()
    with open(README, "w") as f:
        f.write(splice(text, render(merged, len(search_prs("is:open")), info)))


def test():
    pr = lambda n: {"number": n, "html_url": f"https://x/pull/{n}", "title": "fix `a|b`"}
    out = render({"a/big": [pr(i) for i in range(5)], "b/small": [pr(9)]}, 2,
                 {"a/big": (1500, "main", 5), "b/small": (7, "master", 1)})
    assert out["summary"] == "6 merged PRs in 2 projects, 2 more open."
    assert out["contributions"].index("a/big") < out["contributions"].index("b/small")  # sorted by stars
    assert "[View all](https://github.com/a/big/pulls?" in out["contributions"] and "[#9](https://x/pull/9)" in out["contributions"]
    doc = "x\n<!-- START_SECTION:summary -->\nold\n<!-- END_SECTION:summary -->\ny"
    want = "x\n<!-- START_SECTION:summary -->\nnew\n<!-- END_SECTION:summary -->\ny"
    assert splice(doc, {"summary": "new"}) == want
    assert splice("x\n<!-- START_SECTION:summary --><!-- END_SECTION:summary -->\ny", {"summary": "new"}) == want  # empty markers
    import xml.etree.ElementTree as ET
    cards = [card("a/b<c", [pr(1), pr(2)], {"description": "x & y " * 20, "language": "Rust"}),
             card("d/e", [pr(i) for i in range(4)], {"description": None, "language": None})]
    assert cards[0]["badge"] == "PR #1 · #2" and cards[1]["badge"] == "4 PRS MERGED"
    ET.fromstring(render_svg(cards))  # valid XML despite <, & in data
    print("ok")


if __name__ == "__main__":
    test() if "--test" in sys.argv else main()
