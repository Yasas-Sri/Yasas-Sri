"""Render whoami.svg: an animated terminal that types each command, then shows its output.

Edit SESSION below and run: python scripts/terminal.py   (--test to self-check)
"""
import os, sys
from xml.sax.saxutils import escape

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
SIZE, CHAR_W = 16, 9.6  # ponytail: assumes the monospace font is 0.6em wide; tweak CHAR_W if the cursor drifts
PROMPT = [("yasas@github", "#3fb950"), (":~", "#58a6ff"), ("$ ", "#a78bfa")]
DIM, TEXT = "#8b949e", "#c9d1d9"

# (command, output segments as (text, color))
SESSION = [
    ("whoami", [("Yasas Sri", "#22d3ee"), (" — open source contributor.", TEXT)]),
    ("cat current_contributing_projects.txt", [("Meshery", "#f0b429"), (" · ", DIM), ("Station House", "#f0b429"), (" · ", DIM), ("geo-sleuth", "#f0b429")]),
    ("cat interests.txt", [("AI agents & tooling · ML research · ML systems · kernels & low-level stuff", TEXT)]),
    ("cat languages.txt", [("Rust", "#dea584"), (" · ", DIM), ("Python", "#6a9fd4"), (" · ", DIM), ("TypeScript", "#3178c6"),
                           (" · ", DIM), ("Go", "#00ADD8"), (" · ", DIM), ("C", TEXT)]),
]
TYPE, PAUSE, GAP, HOLD = 0.09, 0.35, 0.6, 5.0  # seconds: per char, before typing / output, between commands, at the end
OUT = os.path.join(os.path.dirname(__file__), "..", "whoami.svg")


def render(session):
    pw = CHAR_W * sum(len(t) for t, _ in PROMPT)
    longest = max(max(len(c) * CHAR_W + pw, sum(len(t) for t, _ in o) * CHAR_W) for c, o in session)
    W = int(max(600, 36 + longest + 40))
    # timeline: (kind, y, start_s, payload)
    events, t, y = [], 0.4, 80
    for cmd, out in session:
        events.append(("prompt", y, t, None))
        t += PAUSE
        events.append(("type", y, t, cmd))
        t += TYPE * len(cmd) + PAUSE
        events.append(("line", y + 28, t, out))
        t += GAP
        y += 66
    events.append(("prompt", y, t, None))
    events.append(("cursor", y, t, None))
    dur = t + HOLD
    H = y + 30
    k = lambda s: f"{s / dur:.5f}"
    end = k(dur - 0.6)  # everything vanishes just before the loop restarts
    show = lambda s: (f'<animate attributeName="opacity" calcMode="discrete" dur="{dur:.1f}s" repeatCount="indefinite" '
                      f'values="0;1;0" keyTimes="0;{k(s)};{end}"/>')
    text = lambda x, y, inner, extra="": f'<text xml:space="preserve" x="{x}" y="{y}" {extra}font-family="{FONT}" font-size="{SIZE}">{inner}</text>'
    spans = lambda segs: "".join(f'<tspan fill="{c}">{escape(s)}</tspan>' for s, c in segs)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + 20}" viewBox="0 0 {W} {H + 20}" role="img" aria-label="Terminal: about Yasas">',
           '<style>.blink{animation:blink 1s steps(1) infinite}@keyframes blink{50%{opacity:0}}</style>',
           f'<rect x="10" y="10" width="{W - 20}" height="{H}" rx="14" fill="#0d1117" stroke="#30363d"/>',
           f'<path d="M10 46 V24 a14 14 0 0 1 14 -14 H{W - 24} a14 14 0 0 1 14 14 V46 Z" fill="#161b22"/>',
           f'<line x1="10" y1="46" x2="{W - 10}" y2="46" stroke="#30363d"/>',
           '<circle cx="34" cy="28" r="6.5" fill="#ff5f57"/><circle cx="56" cy="28" r="6.5" fill="#febc2e"/><circle cx="78" cy="28" r="6.5" fill="#28c840"/>',
           f'<text x="{W / 2}" y="32.5" text-anchor="middle" font-family="{FONT}" font-size="13" fill="{DIM}">yasas@github: ~</text>']
    defs = []
    for i, (kind, y, s, payload) in enumerate(events):
        if kind == "prompt":
            out.append(f'<g opacity="0">{show(s)}{text(36, y, spans(PROMPT))}</g>')
        elif kind == "line":
            out.append(f'<g opacity="0">{show(s)}{text(36, y, spans(payload))}</g>')
        elif kind == "cursor":
            out.append(f'<g opacity="0">{show(s)}<rect class="blink" x="{36 + pw + 1:.1f}" y="{y - 15}" width="10" height="20" fill="#e6edf3"/></g>')
        else:  # type: widen a clip rect one character per step
            n = len(payload)
            widths = ";".join(f"{CHAR_W * j:g}" for j in range(n + 1))
            times = ";".join(k(s + TYPE * j) for j in range(n + 1))
            defs.append(f'<clipPath id="c{i}"><rect x="{36 + pw:.1f}" y="{y - 16}" width="0" height="22">'
                        f'<animate attributeName="width" calcMode="discrete" dur="{dur:.1f}s" repeatCount="indefinite" '
                        f'values="0;{widths};0" keyTimes="0;{times};{end}"/></rect></clipPath>')
            out.append(text(f"{36 + pw:.1f}", y, escape(payload), f'clip-path="url(#c{i})" fill="#e6edf3" '))
    out.insert(2, f"<defs>{''.join(defs)}</defs>")
    return "\n".join(out + ["</svg>"])


def test():
    import xml.etree.ElementTree as ET
    svg = render(SESSION)
    ET.fromstring(svg)  # valid XML (the & in interests is escaped)
    for a in ET.fromstring(svg).iter("{http://www.w3.org/2000/svg}animate"):
        kt = [float(x) for x in a.get("keyTimes").split(";")]
        assert kt == sorted(kt) and kt[0] == 0 and kt[-1] < 1, kt  # SMIL needs increasing keyTimes in [0,1]
        assert len(kt) == len(a.get("values").split(";"))
    print("ok")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test()
    else:
        with open(OUT, "w") as f:
            f.write(render(SESSION))
