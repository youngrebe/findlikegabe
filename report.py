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
):
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{target_steamID}_{timestamp}.html"

    creation_str = (
        datetime.fromtimestamp(int(target_creation_date)).strftime("%d %b %Y")
        if target_creation_date
        else "Unknown"
    )
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Graph nodes / links ──────────────────────────────────────────────────
    nodes = [
        {
            "id": target_steamID,
            "label": target_nickname,
            "avatar": target_avatar,
            "type": "target",
        }
    ]
    links = []
    seen = {target_steamID}

    for s in FRIEND_SUMMARIES:
        if s.steamID not in seen:
            nodes.append(
                {
                    "id": s.steamID,
                    "label": s.nickname,
                    "avatar": s.avatar,
                    "type": "friend",
                    "since": s.since,
                }
            )
            seen.add(s.steamID)
        links.append({"source": target_steamID, "target": s.steamID, "type": "friend"})

    for s in CONNECTION_SUMMARIES:
        if s.steamID not in seen:
            nodes.append(
                {
                    "id": s.steamID,
                    "label": s.nickname,
                    "avatar": s.avatar,
                    "type": "connection",
                    "since": s.since,
                }
            )
            seen.add(s.steamID)
        links.append(
            {"source": target_steamID, "target": s.steamID, "type": "connection"}
        )

    graph_json = json.dumps({"nodes": nodes, "links": links})

    # ── HTML helpers ─────────────────────────────────────────────────────────
    def archive_rows(items, val_attr):
        if not items:
            return '<tr><td colspan="2" class="empty-cell">- no data -</td></tr>'
        out = ""
        for item in items:
            val = getattr(item, val_attr, "")
            date = getattr(item, "date", "")
            out += f"<tr><td>{val}</td><td class='mono dim'>{date}</td></tr>"
        return out

    def avatar_grid():
        if not ARCHIVE_AVATARS:
            return '<p class="empty-cell">- no data -</p>'
        out = '<div class="avatar-grid">'
        for av in ARCHIVE_AVATARS:
            out += f'<div class="av-item"><img src="{av.url}" alt=""><span class="mono">{av.date}</span></div>'
        out += "</div>"
        return out

    def fmt_ts(ts):
        try:
            return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError, OSError):
            return str(ts)

    # lookup: steamID → (nickname, avatar)
    known = {}
    for s in FRIEND_SUMMARIES + CONNECTION_SUMMARIES:
        known[s.steamID] = (s.nickname, s.avatar)

    def comments_html():
        if not COMMENTS:
            return '<p class="empty-cell">- no comments found -</p>'
        out = ""
        for c in COMMENTS:
            text = str(c.text).replace("<", "&lt;").replace(">", "&gt;")
            date = fmt_ts(c.publishedAt)
            nickname, avatar = known.get(c.authorID, (c.authorID, None))
            ava_html = f'<img src="{avatar}" class="comment-ava">' if avatar else f'<div class="comment-ava-placeholder"></div>'
            profile_url = f"https://steamcommunity.com/profiles/{c.authorID}"
            out += f"""
            <div class="comment-card">
                <div class="comment-header">
                    <a href="{profile_url}" target="_blank" class="comment-profile-link">{ava_html}</a>
                    <div class="comment-author">
                        <a href="{profile_url}" target="_blank" class="comment-nick">{nickname}</a>
                        <span class="mono dim" style="font-size:10px">{c.authorID}</span>
                    </div>
                    <span class="mono dim" style="margin-left:auto">{date}</span>
                </div>
                <div class="comment-body">{text}</div>
            </div>"""
        return out

    def people_rows(summaries, kind, color):
        if not summaries:
            return f'<tr><td colspan="5" class="empty-cell">- no {kind}s -</td></tr>'
        out = ""
        for s in summaries:
            out += f"""
            <tr>
                <td><img src="{s.avatar}" class="row-avatar"></td>
                <td>{s.nickname}</td>
                <td class="mono dim" style="font-size:11px">{s.steamID}</td>
                <td class="mono dim">{s.since}</td>
                <td><span class="badge" style="background:{color}22;border-color:{color};color:{color}">{kind}</span></td>
            </tr>"""
        return out

    # ── HTML ─────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{target_nickname}</title>
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}

:root{{
  --bg:#0e1419;--bg2:#171d25;--bg3:#1e2a35;
  --panel:#1b2838;--border:#2a475e;
  --accent:#66c0f4;--accent2:#1b9bd1;
  --gold:#c6a850;--green:#a4d007;--red:#c94040;
  --text:#c7d5e0;--dim:#698fa8;
}}

body{{background:var(--bg);color:var(--text);font-family:'Barlow',sans-serif;font-weight:400;line-height:1.5;min-height:100vh}}
body::after{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,.05) 3px,rgba(0,0,0,.05) 4px);pointer-events:none;z-index:9999}}

/* HEADER */
.header{{background:linear-gradient(160deg,#0a1520 0%,#1b2838 40%,#0f1c28 100%);border-bottom:2px solid var(--border);position:relative;overflow:hidden}}
.hglow{{position:absolute;top:-60px;left:50%;transform:translateX(-50%);width:700px;height:180px;background:radial-gradient(ellipse,rgba(102,192,244,.1) 0%,transparent 70%);pointer-events:none}}
.header-inner{{max-width:1380px;margin:0 auto;padding:32px 40px;display:flex;align-items:center;gap:28px;position:relative;z-index:1}}
.target-ava{{width:96px;height:96px;border:3px solid var(--gold);box-shadow:0 0 0 1px rgba(198,168,80,.25),0 0 28px rgba(198,168,80,.2);flex-shrink:0;image-rendering:pixelated}}
.header-text h1{{font-family:'Rajdhani',sans-serif;font-size:36px;font-weight:700;color:#fff;letter-spacing:.5px;line-height:1}}
.steam-id{{font-family:'Share Tech Mono',monospace;color:var(--accent);font-size:12px;margin-top:5px;letter-spacing:.5px}}
.chips{{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}}
.chip{{font-family:'Share Tech Mono',monospace;font-size:11px;padding:3px 10px;border:1px solid var(--border);background:rgba(102,192,244,.06);color:var(--dim)}}
.chip b{{color:var(--accent)}}
.header-ts{{margin-left:auto;text-align:right;font-family:'Share Tech Mono',monospace;font-size:11px;color:var(--dim);line-height:2;flex-shrink:0}}
.ts-lbl{{color:var(--accent);display:block;font-size:10px;letter-spacing:1px}}

/* STATS */
.statsbar{{background:var(--bg2);border-bottom:1px solid var(--border);padding:14px 40px;display:flex;justify-content:center;gap:50px;flex-wrap:wrap}}
.stat{{display:flex;flex-direction:column;align-items:center;gap:2px}}
.stat-n{{font-family:'Rajdhani',sans-serif;font-size:30px;font-weight:700;line-height:1}}
.stat-n.gold{{color:var(--gold)}}.stat-n.green{{color:var(--green)}}.stat-n.blue{{color:var(--accent)}}.stat-n.red{{color:var(--red)}}
.stat-l{{font-size:10px;font-weight:500;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim)}}

/* NAV */
.nav{{background:var(--bg2);border-bottom:1px solid var(--border);display:flex;justify-content:center;padding:0 40px;overflow-x:auto}}
.nav-tab{{font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:600;letter-spacing:1px;text-transform:uppercase;padding:14px 20px;color:var(--dim);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:color .2s,border-color .2s;user-select:none}}
.nav-tab:hover{{color:var(--text)}}
.nav-tab.active{{color:var(--accent);border-bottom-color:var(--accent)}}

/* PAGES */
.page{{display:none;max-width:1380px;margin:0 auto;padding:28px 40px}}
.page.active{{display:block}}

/* PANEL */
.panel{{background:var(--bg2);border:1px solid var(--border);margin-bottom:20px;position:relative}}
.panel::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),transparent 70%)}}
.panel-title{{font-family:'Rajdhani',sans-serif;font-size:15px;font-weight:600;letter-spacing:2px;text-transform:uppercase;color:var(--accent);padding:13px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}}
.panel-title::before{{content:'';width:7px;height:7px;background:var(--accent);clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%);flex-shrink:0}}
.panel-body{{padding:20px}}

/* GRAPH */
#graph-wrap{{background:var(--bg);border:1px solid var(--border);position:relative;height:580px;overflow:hidden}}
#graph-svg{{width:100%;height:100%}}
.graph-legend{{position:absolute;bottom:14px;left:14px;display:flex;gap:14px;flex-wrap:wrap}}
.leg-item{{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim);font-family:'Share Tech Mono',monospace}}
.leg-dot{{width:9px;height:9px;border-radius:50%}}
.gtip{{position:absolute;background:var(--panel);border:1px solid var(--border);padding:8px 12px;font-size:12px;font-family:'Share Tech Mono',monospace;pointer-events:none;display:none;white-space:nowrap;z-index:10;box-shadow:0 4px 20px rgba(0,0,0,.5)}}

/* TABLES */
.data-table{{width:100%;border-collapse:collapse}}
.data-table th{{font-family:'Rajdhani',sans-serif;font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--dim);padding:8px 12px;border-bottom:1px solid var(--border);text-align:left}}
.data-table td{{padding:8px 12px;border-bottom:1px solid rgba(42,71,94,.5);vertical-align:middle}}
.data-table tr:last-child td{{border-bottom:none}}
.data-table tr:hover td{{background:rgba(102,192,244,.04)}}
.row-avatar{{width:32px;height:32px;border:1px solid var(--border)}}
.badge{{display:inline-block;padding:2px 8px;font-size:10px;border:1px solid;font-family:'Share Tech Mono',monospace;letter-spacing:.5px}}

/* ARCHIVE */
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.avatar-grid{{display:flex;flex-wrap:wrap;gap:12px}}
.av-item{{display:flex;flex-direction:column;align-items:center;gap:4px}}
.av-item img{{width:64px;height:64px;border:1px solid var(--border);image-rendering:pixelated}}
.av-item span{{font-size:10px;color:var(--dim)}}

/* COMMENTS */
.comments-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.comment-card{{background:var(--bg3);border:1px solid var(--border);border-left:3px solid var(--accent2);padding:12px 14px}}
.comment-header{{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:11px}}
.comment-ava{{width:28px;height:28px;border:1px solid var(--border);flex-shrink:0;image-rendering:pixelated}}
.comment-ava-placeholder{{width:28px;height:28px;background:var(--border);flex-shrink:0}}
.comment-author{{display:flex;flex-direction:column;gap:1px;min-width:0}}
.comment-nick{{color:var(--accent);font-family:'Share Tech Mono',monospace;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-decoration:none}}
.comment-nick:hover{{color:#fff;text-decoration:underline}}
.comment-profile-link{{display:flex;flex-shrink:0}}
.comment-profile-link:hover .comment-ava{{border-color:var(--accent);box-shadow:0 0 8px rgba(102,192,244,.4)}}
.comment-body{{font-size:13px;color:var(--text);line-height:1.4;white-space:pre-wrap;word-break:break-word}}

/* UTILS */
.mono{{font-family:'Share Tech Mono',monospace}}
.dim{{color:var(--dim)}}
.accent{{color:var(--accent)}}
.empty-cell{{text-align:center;color:var(--dim);font-family:'Share Tech Mono',monospace;font-size:12px;padding:20px}}

@media(max-width:900px){{
  .header-inner,.statsbar,.nav,.page{{padding-left:16px;padding-right:16px}}
  .two-col,.comments-grid{{grid-template-columns:1fr}}
  .header-ts{{display:none}}
}}
</style>
</head>
<body>

<div class="header">
  <div class="hglow"></div>
  <div class="header-inner">
    <img class="target-ava" src="{target_avatar}" alt="avatar">
    <div class="header-text">
      <h1>{target_nickname}</h1>
      <div class="steam-id">{target_steamID}</div>
      <div class="chips">
        <span class="chip">CREATED <b>{creation_str}</b></span>
        <span class="chip">FRIENDS <b>{len(FRIEND_SUMMARIES)}</b></span>
        <span class="chip">CONNECTIONS <b>{len(CONNECTION_SUMMARIES)}</b></span>
        <span class="chip">COMMENTS <b>{len(COMMENTS)}</b></span>
      </div>
    </div>
    <div class="header-ts">
      <span class="ts-lbl">REPORT GENERATED</span>
      {report_time}<br>FINDLIKEGABE
    </div>
  </div>
</div>

<div class="statsbar">
  <div class="stat"><span class="stat-n gold">{len(FRIEND_SUMMARIES)}</span><span class="stat-l">Friends</span></div>
  <div class="stat"><span class="stat-n blue">{len(CONNECTION_SUMMARIES)}</span><span class="stat-l">Connections</span></div>
  <div class="stat"><span class="stat-n green">{len(COMMENTS)}</span><span class="stat-l">Comments</span></div>
  <div class="stat"><span class="stat-n red">{len(ARCHIVE_NICKNAMES)}</span><span class="stat-l">Name History</span></div>
  <div class="stat"><span class="stat-n gold">{len(ARCHIVE_AVATARS)}</span><span class="stat-l">Avatar History</span></div>
  <div class="stat"><span class="stat-n blue">{len(nodes)}</span><span class="stat-l">Graph Nodes</span></div>
</div>

<div class="nav">
  <div class="nav-tab active" data-tab="graph">SOCMINT</div>
  <div class="nav-tab" data-tab="friends">Friends &amp; Connections</div>
  <div class="nav-tab" data-tab="comments">Comments</div>
  <div class="nav-tab" data-tab="archive">Archive</div>
</div>

<!-- GRAPH -->
<div class="page active" id="tab-graph">
  <div class="panel">
    <div class="panel-title">Social Connection Graph - {len(nodes)} nodes / {len(links)} edges</div>
    <div id="graph-wrap">
      <svg id="graph-svg"></svg>
      <div class="graph-legend">
        <div class="leg-item"><div class="leg-dot" style="background:#c6a850"></div>Target</div>
        <div class="leg-item"><div class="leg-dot" style="background:#a4d007"></div>Friend</div>
        <div class="leg-item"><div class="leg-dot" style="background:#66c0f4"></div>Connection</div>
      </div>
      <div class="gtip" id="gtip"></div>
    </div>
  </div>
</div>

<!-- FRIENDS -->
<div class="page" id="tab-friends">
  <div class="panel">
    <div class="panel-title">Friends ({len(FRIEND_SUMMARIES)})</div>
    <div class="panel-body" style="padding:0;overflow-x:auto">
      <table class="data-table">
        <thead><tr><th></th><th>Nickname</th><th>SteamID</th><th>Friends Since</th><th>Type</th></tr></thead>
        <tbody>{people_rows(FRIEND_SUMMARIES,'friend','#a4d007')}</tbody>
      </table>
    </div>
  </div>
  <div class="panel">
    <div class="panel-title">Connections ({len(CONNECTION_SUMMARIES)})</div>
    <div class="panel-body" style="padding:0;overflow-x:auto">
      <table class="data-table">
        <thead><tr><th></th><th>Nickname</th><th>SteamID</th><th>Since</th><th>Type</th></tr></thead>
        <tbody>{people_rows(CONNECTION_SUMMARIES,'connection','#66c0f4')}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- COMMENTS -->
<div class="page" id="tab-comments">
  <div class="panel">
    <div class="panel-title">Profile Comments ({len(COMMENTS)})</div>
    <div class="panel-body">
      <div class="comments-grid">{comments_html()}</div>
    </div>
  </div>
</div>

<!-- ARCHIVE -->
<div class="page" id="tab-archive">
  <div class="two-col">
    <div class="panel">
      <div class="panel-title">Nickname History ({len(ARCHIVE_NICKNAMES)})</div>
      <div class="panel-body" style="padding:0;overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Nickname</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_NICKNAMES,'nickname')}</tbody>
        </table>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Real Name History ({len(ARCHIVE_REAL_NAMES)})</div>
      <div class="panel-body" style="padding:0;overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>Real Name</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_REAL_NAMES,'realname')}</tbody>
        </table>
      </div>
    </div>
  </div>
  <div class="two-col">
    <div class="panel">
      <div class="panel-title">URL History ({len(ARCHIVE_URLS)})</div>
      <div class="panel-body" style="padding:0;overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>URL</th><th>Date</th></tr></thead>
          <tbody>{archive_rows(ARCHIVE_URLS,'url')}</tbody>
        </table>
      </div>
    </div>
    <div class="panel">
      <div class="panel-title">Avatar History ({len(ARCHIVE_AVATARS)})</div>
      <div class="panel-body">{avatar_grid()}</div>
    </div>
  </div>
</div>

<script>
// ── Tabs ─────────────────────────────────────────────────────────────────────
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

// ── D3 Graph ──────────────────────────────────────────────────────────────────
const GRAPH = {graph_json};
let graphInited = false;

function initGraph() {{
  if (graphInited) return;
  graphInited = true;

  const wrap = document.getElementById('graph-wrap');
  const W = wrap.clientWidth, H = wrap.clientHeight;
  const tip = document.getElementById('gtip');
  const colors = {{ target: '#c6a850', friend: '#a4d007', connection: '#66c0f4' }};

  const svg = d3.select('#graph-svg');
  const g   = svg.append('g');

  svg.call(
    d3.zoom().scaleExtent([.15, 4])
      .on('zoom', e => g.attr('transform', e.transform))
  );

  const sim = d3.forceSimulation(GRAPH.nodes)
    .force('link',    d3.forceLink(GRAPH.links).id(d => d.id).distance(d => d.type === 'friend' ? 110 : 150).strength(.5))
    .force('charge',  d3.forceManyBody().strength(-350))
    .force('center',  d3.forceCenter(W / 2, H / 2))
    .force('collide', d3.forceCollide(24));

  const defs = svg.append('defs');

  // Gradient for links
  defs.append('marker').attr('id','arr-f').attr('viewBox','0 -4 8 8').attr('refX',18).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#a4d00766');
  defs.append('marker').attr('id','arr-c').attr('viewBox','0 -4 8 8').attr('refX',16).attr('markerWidth',5).attr('markerHeight',5).attr('orient','auto')
    .append('path').attr('d','M0,-4L8,0L0,4').attr('fill','#66c0f455');

  const link = g.append('g').selectAll('line').data(GRAPH.links).join('line')
    .attr('stroke',       d => d.type === 'friend' ? '#a4d00760' : '#66c0f445')
    .attr('stroke-width', d => d.type === 'friend' ? 1.5 : 1)
    .attr('marker-end',   d => d.type === 'friend' ? 'url(#arr-f)' : 'url(#arr-c)');

  const node = g.append('g').selectAll('g').data(GRAPH.nodes).join('g')
    .attr('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (e, d) => {{ if (!e.active) sim.alphaTarget(.3).restart(); d.fx = d.x; d.fy = d.y; }})
      .on('drag',  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
      .on('end',   (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }})
    );

  // Outer glow ring for target
  node.filter(d => d.type === 'target').append('circle')
    .attr('r', 30).attr('fill', 'none')
    .attr('stroke', '#c6a850').attr('stroke-width', 1).attr('opacity', .35)
    .attr('stroke-dasharray', '4 3');

  // Main circle
  node.append('circle')
    .attr('r', d => d.type === 'target' ? 22 : 13)
    .attr('fill',         d => colors[d.type] + '20')
    .attr('stroke',       d => colors[d.type])
    .attr('stroke-width', d => d.type === 'target' ? 2.5 : 1.5);

  // Clip paths for avatars
  GRAPH.nodes.forEach((d, i) => {{
    const r = d.type === 'target' ? 20 : 11;
    defs.append('clipPath').attr('id', `cl${{i}}`).append('circle').attr('r', r);
    if (d.avatar) {{
      node.filter((nd, ni) => ni === i)
        .append('image')
        .attr('href', d.avatar)
        .attr('x', -r).attr('y', -r)
        .attr('width', r * 2).attr('height', r * 2)
        .attr('clip-path', `url(#cl${{i}})`);
    }}
  }});

  // Label
  node.append('text')
    .text(d => d.label.length > 14 ? d.label.slice(0, 13) + '…' : d.label)
    .attr('y',            d => (d.type === 'target' ? 22 : 13) + 13)
    .attr('text-anchor',  'middle')
    .attr('fill',         d => colors[d.type])
    .attr('font-size',    d => d.type === 'target' ? '11px' : '9px')
    .attr('font-family',  "'Share Tech Mono', monospace");

  // Tooltip + click → Steam profile
  node
    .on('mouseover', (e, d) => {{
      tip.style.display = 'block';
      tip.innerHTML = `<span style="color:${{colors[d.type]}}">${{d.type.toUpperCase()}}</span>  ${{d.label}}<br><span style="color:#698fa8">${{d.id}}</span>${{d.since ? '<br>since ' + d.since : ''}}<br><span style="color:#698fa8;font-size:10px">click to open profile</span>`;
    }})
    .on('mousemove', e => {{
      const r = wrap.getBoundingClientRect();
      tip.style.left = (e.clientX - r.left + 14) + 'px';
      tip.style.top  = (e.clientY - r.top  + 14) + 'px';
    }})
    .on('mouseout', () => tip.style.display = 'none')
    .on('click', (e, d) => {{
      // only fire on click, not after drag
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

    print(f"\n✨ Report saved -> {filename}")
    return filename