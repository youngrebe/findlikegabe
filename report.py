import os
import json
from datetime import datetime


def generate_report(
    target_steamID,
    target_nickname,
    target_avatar,
    target_creation_date,
    ARCHIVE_NICKNAMES,
    ARCHIVE_REAL_NAMES,
    ARCHIVE_URLS,
    ARCHIVE_AVATARS,
    FRIEND_SUMMARIES,
    CONNECTION_SUMMARIES,
    COMMENTS,
    TARGET_COMMENTS_ON_CONNECTIONS,  # list of (profile_steamID, COMMENT)
):
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{target_steamID}_{timestamp}.html"

    creation_str = (
        datetime.fromtimestamp(int(target_creation_date)).strftime("%d %b %Y")
        if target_creation_date
        else "Unknown"
    )
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Graph data ───────────────────────────────────────────────────────────────
    nodes = [{"id": target_steamID, "label": target_nickname, "avatar": target_avatar, "type": "target"}]
    links = []
    seen = {target_steamID}

    for s in FRIEND_SUMMARIES:
        if s.steamID not in seen:
            nodes.append({"id": s.steamID, "label": s.nickname, "avatar": s.avatar, "type": "friend", "since": s.since})
            seen.add(s.steamID)
        links.append({"source": target_steamID, "target": s.steamID, "type": "friend"})

    for s in CONNECTION_SUMMARIES:
        if s.steamID not in seen:
            nodes.append({"id": s.steamID, "label": s.nickname, "avatar": s.avatar, "type": "connection", "since": s.since})
            seen.add(s.steamID)
        links.append({"source": target_steamID, "target": s.steamID, "type": "connection"})

    graph_json = json.dumps({"nodes": nodes, "links": links})

    # ── Helpers ──────────────────────────────────────────────────────────────────
    def fmt_ts(ts):
        try:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError, OSError):
            return str(ts)

    # steamID → (nickname, avatar) for all known people
    known = {}
    for s in FRIEND_SUMMARIES + CONNECTION_SUMMARIES:
        known[s.steamID] = (s.nickname, s.avatar)

    def archive_rows(items, val_attr):
        if not items:
            return '<tr><td colspan="2" class="empty">— no data —</td></tr>'
        out = ""
        for item in items:
            val = getattr(item, val_attr, "")
            date = getattr(item, "date", "")
            out += f'<tr><td>{val}</td><td class="mono muted">{date}</td></tr>'
        return out

    def avatar_grid():
        if not ARCHIVE_AVATARS:
            return '<p class="empty">— no data —</p>'
        out = '<div class="av-grid">'
        for av in ARCHIVE_AVATARS:
            out += f'<div class="av-item"><img src="{av.url}" alt=""><span class="mono muted">{av.date}</span></div>'
        out += "</div>"
        return out

    def render_comments(comment_list):
        """Render list of COMMENT objects (comments on target's own profile)."""
        if not comment_list:
            return '<p class="empty">— no comments —</p>'
        out = '<div class="comment-list">'
        for c in comment_list:
            text = str(c.text).replace("<", "&lt;").replace(">", "&gt;")
            date = fmt_ts(c.publishedAt)
            nickname, avatar = known.get(c.authorID, (c.authorID, None))
            ava_html = f'<img src="{avatar}" class="c-ava">' if avatar else '<div class="c-ava c-ava-ph"></div>'
            profile_url = f"https://steamcommunity.com/profiles/{c.authorID}"
            out += f"""<div class="c-card">
  <div class="c-head">
    <a href="{profile_url}" target="_blank">{ava_html}</a>
    <div class="c-meta">
      <a href="{profile_url}" target="_blank" class="c-nick">{nickname}</a>
      <span class="mono muted xs">{c.authorID}</span>
    </div>
    <span class="mono muted xs ml-auto">{date}</span>
  </div>
  <div class="c-body">{text}</div>
</div>"""
        out += "</div>"
        return out

    def render_target_comments(entries):
        """
        Render TARGET_COMMENTS_ON_CONNECTIONS.
        entries: list of (profile_steamID, COMMENT)
        Groups by profile and shows where the target left each comment.
        """
        if not entries:
            return '<p class="empty">— no comments found —</p>'

        out = '<div class="comment-list">'
        for profile_id, c in entries:
            text = str(c.text).replace("<", "&lt;").replace(">", "&gt;")
            date = fmt_ts(c.publishedAt)
            # Profile that was commented on
            profile_nickname, profile_avatar = known.get(profile_id, (profile_id, None))
            p_ava = f'<img src="{profile_avatar}" class="c-ava">' if profile_avatar else '<div class="c-ava c-ava-ph"></div>'
            profile_url = f"https://steamcommunity.com/profiles/{profile_id}"
            out += f"""<div class="c-card tc-card">
  <div class="tc-on">
    on <a href="{profile_url}" target="_blank" class="tc-profile-link">{p_ava}<span>{profile_nickname}</span></a>
    <span class="mono muted xs ml-auto">{date}</span>
  </div>
  <div class="c-body">{text}</div>
</div>"""
        out += "</div>"
        return out

    def people_rows(summaries, kind, color):
        if not summaries:
            return f'<tr><td colspan="5" class="empty">— no {kind}s —</td></tr>'
        out = ""
        for s in summaries:
            out += f"""<tr>
  <td><img src="{s.avatar}" class="r-ava"></td>
  <td>{s.nickname}</td>
  <td class="mono muted xs">{s.steamID}</td>
  <td class="mono muted">{s.since}</td>
  <td><span class="badge" style="--c:{color}">{kind}</span></td>
</tr>"""
        return out

    # ── HTML ─────────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{target_nickname} — OSINT</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:    #0d0d0d;
  --bg1:   #111111;
  --bg2:   #161616;
  --bg3:   #1a1a1a;
  --line:  #222222;
  --line2: #2a2a2a;
  --text:  #d4d4d4;
  --muted: #555555;
  --acc:   #e8e8e8;
  --green: #4ade80;
  --blue:  #60a5fa;
  --amber: #fbbf24;
  --red:   #f87171;
  --purple:#c084fc;
}}

body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  font-weight: 400;
  line-height: 1.6;
  min-height: 100vh;
}}

a {{ color: inherit; text-decoration: none; }}
.mono {{ font-family: 'JetBrains Mono', monospace; }}
.muted {{ color: var(--muted); }}
.xs {{ font-size: 11px; }}
.ml-auto {{ margin-left: auto; }}

/* ── HEADER ── */
.hdr {{
  border-bottom: 1px solid var(--line);
  background: var(--bg1);
  padding: 24px 40px;
  display: flex;
  align-items: center;
  gap: 20px;
}}
.hdr-ava {{
  width: 56px; height: 56px;
  border: 1px solid var(--line2);
  flex-shrink: 0;
  image-rendering: pixelated;
}}
.hdr-name {{ font-size: 20px; font-weight: 600; color: var(--acc); line-height: 1.2; }}
.hdr-id {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); margin-top: 3px; }}
.hdr-chips {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
.chip {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid var(--line2);
  color: var(--muted);
  letter-spacing: .5px;
}}
.chip b {{ color: var(--text); font-weight: 500; }}
.hdr-ts {{ margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); text-align: right; flex-shrink: 0; }}

/* ── STATS BAR ── */
.stats {{ background: var(--bg1); border-bottom: 1px solid var(--line); display: flex; justify-content: center; }}
.stat {{
  padding: 14px 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border-right: 1px solid var(--line);
}}
.stat:first-child {{ border-left: 1px solid var(--line); }}
.stat-n {{ font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 500; line-height: 1; }}
.stat-n.g {{ color: var(--green); }}
.stat-n.b {{ color: var(--blue); }}
.stat-n.a {{ color: var(--amber); }}
.stat-n.r {{ color: var(--red); }}
.stat-n.p {{ color: var(--purple); }}
.stat-l {{ font-size: 10px; color: var(--muted); letter-spacing: 1px; text-transform: uppercase; }}

/* ── NAV ── */
.nav {{ background: var(--bg1); border-bottom: 1px solid var(--line); display: flex; justify-content: center; padding: 0 40px; overflow-x: auto; }}
.nav-tab {{
  font-size: 11px; font-weight: 500; letter-spacing: 1.2px; text-transform: uppercase;
  padding: 12px 16px; color: var(--muted); cursor: pointer;
  border-bottom: 1px solid transparent; white-space: nowrap;
  transition: color .15s, border-color .15s; user-select: none;
  font-family: 'JetBrains Mono', monospace;
}}
.nav-tab:hover {{ color: var(--text); }}
.nav-tab.active {{ color: var(--acc); border-bottom-color: var(--acc); }}

/* ── PAGES ── */
.page {{ display: none; max-width: 1400px; margin: 0 auto; padding: 28px 40px; }}
.page.active {{ display: block; }}

/* ── SECTION ── */
.section {{ background: var(--bg1); border: 1px solid var(--line); margin-bottom: 16px; }}
.section-title {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--muted); padding: 10px 16px; border-bottom: 1px solid var(--line);
}}
.section-body {{ padding: 16px; }}
.section-body.flush {{ padding: 0; overflow-x: auto; }}

/* ── GRAPH ── */
#graph-wrap {{ background: var(--bg); border: 1px solid var(--line); position: relative; height: 600px; overflow: hidden; }}
#graph-svg {{ width: 100%; height: 100%; }}
.g-legend {{ position: absolute; bottom: 12px; left: 12px; display: flex; gap: 12px; }}
.g-leg {{ display: flex; align-items: center; gap: 5px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--muted); }}
.g-dot {{ width: 7px; height: 7px; border-radius: 50%; }}
.gtip {{ position: absolute; background: var(--bg2); border: 1px solid var(--line2); padding: 8px 12px; font-size: 11px; font-family: 'JetBrains Mono', monospace; pointer-events: none; display: none; white-space: nowrap; z-index: 10; }}

/* ── TABLE ── */
.tbl {{ width: 100%; border-collapse: collapse; }}
.tbl th {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; color: var(--muted); padding: 8px 14px; border-bottom: 1px solid var(--line); text-align: left; }}
.tbl td {{ padding: 7px 14px; border-bottom: 1px solid var(--line); vertical-align: middle; color: var(--text); }}
.tbl tr:last-child td {{ border-bottom: none; }}
.tbl tr:hover td {{ background: var(--bg2); }}
.r-ava {{ width: 28px; height: 28px; border: 1px solid var(--line); image-rendering: pixelated; }}
.badge {{ font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: .5px; padding: 2px 7px; border: 1px solid var(--c, #555); color: var(--c, #555); }}

/* ── 2-COL ── */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}

/* ── AVATAR GRID ── */
.av-grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.av-item {{ display: flex; flex-direction: column; align-items: center; gap: 4px; }}
.av-item img {{ width: 56px; height: 56px; border: 1px solid var(--line); image-rendering: pixelated; }}
.av-item span {{ font-size: 10px; color: var(--muted); }}

/* ── COMMENTS ── */
.comment-list {{ display: flex; flex-direction: column; gap: 1px; }}
.c-card {{ background: var(--bg1); border: 1px solid var(--line); padding: 12px 14px; margin-bottom: 1px; }}
.c-card:last-child {{ margin-bottom: 0; }}
.c-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.c-ava {{ width: 26px; height: 26px; border: 1px solid var(--line); flex-shrink: 0; image-rendering: pixelated; }}
.c-ava-ph {{ background: var(--bg3); }}
.c-meta {{ display: flex; flex-direction: column; gap: 1px; min-width: 0; }}
.c-nick {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--acc); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.c-nick:hover {{ text-decoration: underline; }}
.c-body {{ font-size: 12px; line-height: 1.5; color: var(--text); white-space: pre-wrap; word-break: break-word; }}

/* ── TARGET COMMENTS ── */
.tc-card {{ border-left: 2px solid var(--purple); }}
.tc-on {{
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 8px;
}}
.tc-profile-link {{
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--purple);
}}
.tc-profile-link:hover span {{ text-decoration: underline; }}
.tc-profile-link .c-ava {{ border-color: var(--purple)33; }}

/* ── MISC ── */
.empty {{ text-align: center; color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 24px; }}

@media (max-width: 900px) {{
  .hdr, .stats, .nav, .page {{ padding-left: 16px; padding-right: 16px; }}
  .two-col {{ grid-template-columns: 1fr; }}
  .hdr-ts {{ display: none; }}
  .stat {{ padding: 12px 16px; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<div class="hdr">
  <img class="hdr-ava" src="{target_avatar}" alt="">
  <div>
    <div class="hdr-name">{target_nickname}</div>
    <div class="hdr-id">{target_steamID}</div>
    <div class="hdr-chips">
      <span class="chip">CREATED <b>{creation_str}</b></span>
      <span class="chip">FRIENDS <b>{len(FRIEND_SUMMARIES)}</b></span>
      <span class="chip">CONNECTIONS <b>{len(CONNECTION_SUMMARIES)}</b></span>
      <span class="chip">COMMENTS <b>{len(COMMENTS)}</b></span>
    </div>
  </div>
  <div class="hdr-ts">FINDLIKEGABE<br>{report_time}</div>
</div>

<!-- STATS -->
<div class="stats">
  <div class="stat"><span class="stat-n a">{len(FRIEND_SUMMARIES)}</span><span class="stat-l">Friends</span></div>
  <div class="stat"><span class="stat-n b">{len(CONNECTION_SUMMARIES)}</span><span class="stat-l">Connections</span></div>
  <div class="stat"><span class="stat-n g">{len(COMMENTS)}</span><span class="stat-l">Comments</span></div>
  <div class="stat"><span class="stat-n p">{len(TARGET_COMMENTS_ON_CONNECTIONS)}</span><span class="stat-l">Target's Comments</span></div>
  <div class="stat"><span class="stat-n r">{len(ARCHIVE_NICKNAMES)}</span><span class="stat-l">Nick History</span></div>
  <div class="stat"><span class="stat-n a">{len(ARCHIVE_AVATARS)}</span><span class="stat-l">Avatar History</span></div>
</div>

<!-- NAV -->
<div class="nav">
  <div class="nav-tab active" data-tab="graph">Graph</div>
  <div class="nav-tab" data-tab="people">Friends &amp; Connections</div>
  <div class="nav-tab" data-tab="comments">Comments</div>
  <div class="nav-tab" data-tab="target-comments">Target's Comments <span style="color:var(--purple)">({len(TARGET_COMMENTS_ON_CONNECTIONS)})</span></div>
  <div class="nav-tab" data-tab="archive">Archive</div>
</div>

<!-- GRAPH -->
<div class="page active" id="tab-graph">
  <div class="section">
    <div class="section-title">Social graph — {len(nodes)} nodes / {len(links)} edges</div>
    <div id="graph-wrap">
      <svg id="graph-svg"></svg>
      <div class="g-legend">
        <div class="g-leg"><div class="g-dot" style="background:var(--amber)"></div>Target</div>
        <div class="g-leg"><div class="g-dot" style="background:var(--green)"></div>Friend</div>
        <div class="g-leg"><div class="g-dot" style="background:var(--blue)"></div>Connection</div>
      </div>
      <div class="gtip" id="gtip"></div>
    </div>
  </div>
</div>

<!-- PEOPLE -->
<div class="page" id="tab-people">
  <div class="section">
    <div class="section-title">Friends ({len(FRIEND_SUMMARIES)})</div>
    <div class="section-body flush">
      <table class="tbl">
        <thead><tr><th></th><th>Nickname</th><th>SteamID</th><th>Friends Since</th><th>Type</th></tr></thead>
        <tbody>{people_rows(FRIEND_SUMMARIES, 'friend', '#4ade80')}</tbody>
      </table>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Connections ({len(CONNECTION_SUMMARIES)})</div>
    <div class="section-body flush">
      <table class="tbl">
        <thead><tr><th></th><th>Nickname</th><th>SteamID</th><th>Since</th><th>Type</th></tr></thead>
        <tbody>{people_rows(CONNECTION_SUMMARIES, 'connection', '#60a5fa')}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- COMMENTS ON TARGET'S PROFILE -->
<div class="page" id="tab-comments">
  <div class="section">
    <div class="section-title">Comments on target's profile ({len(COMMENTS)})</div>
    <div class="section-body">
      {render_comments(COMMENTS)}
    </div>
  </div>
</div>

<!-- TARGET'S OWN COMMENTS ON CONNECTIONS -->
<div class="page" id="tab-target-comments">
  <div class="section">
    <div class="section-title">Comments left by target on connections' profiles ({len(TARGET_COMMENTS_ON_CONNECTIONS)})</div>
    <div class="section-body">
      {render_target_comments(TARGET_COMMENTS_ON_CONNECTIONS)}
    </div>
  </div>
</div>

<!-- ARCHIVE -->
<div class="page" id="tab-archive">
  <div class="two-col">
    <div class="section">
      <div class="section-title">Nickname history ({len(ARCHIVE_NICKNAMES)})</div>
      <div class="section-body flush">
        <table class="tbl">
          <thead><tr><th>Nickname</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_NICKNAMES, 'nickname')}</tbody>
        </table>
      </div>
    </div>
    <div class="section">
      <div class="section-title">Real name history ({len(ARCHIVE_REAL_NAMES)})</div>
      <div class="section-body flush">
        <table class="tbl">
          <thead><tr><th>Real Name</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_REAL_NAMES, 'realname')}</tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="two-col">
    <div class="section">
      <div class="section-title">URL history ({len(ARCHIVE_URLS)})</div>
      <div class="section-body flush">
        <table class="tbl">
          <thead><tr><th>URL</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_URLS, 'url')}</tbody>
        </table>
      </div>
    </div>
    <div class="section">
      <div class="section-title">Avatar history ({len(ARCHIVE_AVATARS)})</div>
      <div class="section-body">{avatar_grid()}</div>
    </div>
  </div>
</div>

<script>
// ── Tabs ────────────────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-tab').forEach(tab => {{
  tab.addEventListener('click', () => {{
    const name = tab.dataset.tab;
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + name).classList.add('active');
    if (name === 'graph') initGraph();
  }});
}});

// ── D3 Graph ────────────────────────────────────────────────────────────────────
const GRAPH = {graph_json};
let graphInited = false;

function initGraph() {{
  if (graphInited) return;
  graphInited = true;

  const wrap = document.getElementById('graph-wrap');
  const W = wrap.clientWidth, H = wrap.clientHeight;
  const tip = document.getElementById('gtip');
  const C = {{ target: '#fbbf24', friend: '#4ade80', connection: '#60a5fa' }};

  const svg = d3.select('#graph-svg');
  const g   = svg.append('g');

  svg.call(d3.zoom().scaleExtent([.1, 5]).on('zoom', e => g.attr('transform', e.transform)));

  const sim = d3.forceSimulation(GRAPH.nodes)
    .force('link',    d3.forceLink(GRAPH.links).id(d => d.id).distance(d => d.type === 'friend' ? 100 : 140).strength(.5))
    .force('charge',  d3.forceManyBody().strength(-300))
    .force('center',  d3.forceCenter(W / 2, H / 2))
    .force('collide', d3.forceCollide(20));

  const defs = svg.append('defs');

  const link = g.append('g').selectAll('line').data(GRAPH.links).join('line')
    .attr('stroke', d => d.type === 'friend' ? '#4ade8030' : '#60a5fa25')
    .attr('stroke-width', 1);

  const node = g.append('g').selectAll('g').data(GRAPH.nodes).join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => {{ if (!e.active) sim.alphaTarget(.3).restart(); d.fx = d.x; d.fy = d.y; }})
      .on('drag',  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
      .on('end',   (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }})
    );

  node.append('circle')
    .attr('r', d => d.type === 'target' ? 20 : 12)
    .attr('fill', 'none')
    .attr('stroke', d => C[d.type])
    .attr('stroke-width', d => d.type === 'target' ? 1.5 : 1);

  GRAPH.nodes.forEach((d, i) => {{
    const r = d.type === 'target' ? 18 : 10;
    defs.append('clipPath').attr('id', `cl${{i}}`).append('circle').attr('r', r);
    if (d.avatar) {{
      node.filter((nd, ni) => ni === i)
        .append('image').attr('href', d.avatar)
        .attr('x', -r).attr('y', -r)
        .attr('width', r * 2).attr('height', r * 2)
        .attr('clip-path', `url(#cl${{i}})`);
    }}
  }});

  node.append('text')
    .text(d => d.label.length > 12 ? d.label.slice(0, 11) + '…' : d.label)
    .attr('y', d => (d.type === 'target' ? 20 : 12) + 12)
    .attr('text-anchor', 'middle')
    .attr('fill', d => C[d.type])
    .attr('font-size', d => d.type === 'target' ? '10px' : '8px')
    .attr('font-family', "'JetBrains Mono', monospace");

  node
    .on('mouseover', (e, d) => {{
      tip.style.display = 'block';
      tip.innerHTML = `<span style="color:${{C[d.type]}}">${{d.type}}</span>  ${{d.label}}<br><span style="color:#555">${{d.id}}</span>${{d.since ? '<br>since ' + d.since : ''}}`;
    }})
    .on('mousemove', e => {{
      const r = wrap.getBoundingClientRect();
      tip.style.left = (e.clientX - r.left + 14) + 'px';
      tip.style.top  = (e.clientY - r.top  + 14) + 'px';
    }})
    .on('mouseout', () => tip.style.display = 'none')
    .on('click', (e, d) => {{
      if (e.defaultPrevented) return;
      window.open(`https://steamcommunity.com/profiles/${{d.id}}`, '_blank');
    }});

  sim.on('tick', () => {{
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});
}}

window.addEventListener('load', initGraph);
</script>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)

    return filename
