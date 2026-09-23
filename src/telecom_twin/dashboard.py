"""Dependency-free browser dashboard for the live synthetic twin API."""

DASHBOARD_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Telecom Network Digital Twin</title>
<style>
:root{font-family:Inter,system-ui,sans-serif;color:#dce7f5;background:#07111f}body{margin:0}
header{padding:24px 4vw 12px}h1{margin:0;font-size:clamp(24px,4vw,42px)}p{color:#91a4bd}
main{padding:12px 4vw 40px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card,.panel{background:#0e1d30;border:1px solid #203650;border-radius:14px;padding:16px}
.value{font-size:28px;font-weight:700;color:#5eead4}.grid{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-top:12px}
svg{width:100%;height:560px;background:#091727;border-radius:10px}.link{stroke:#294562;stroke-width:1.5}
.node{stroke:#8ba5c4;stroke-width:1.5}.core{fill:#8b5cf6}.aggregation{fill:#0ea5e9}.access{fill:#14b8a6}.anomaly{fill:#ef4444;stroke:#fecaca;stroke-width:3}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px;border-bottom:1px solid #203650;text-align:left}
button{background:#2563eb;color:white;border:0;padding:9px 14px;border-radius:8px;cursor:pointer}@media(max-width:850px){.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}
</style></head><body><header><h1>Telecom Network Digital Twin</h1><p>Deterministic synthetic streaming telemetry · rolling anomaly detection</p></header>
<main><div class="cards"><div class="card">Time<div class="value" id="time">—</div></div><div class="card">Nodes<div class="value" id="nodes">27</div></div><div class="card">Detections<div class="value" id="events">0</div></div><div class="card">Active<div class="value" id="active">0</div></div></div>
<div class="grid"><section class="panel"><svg id="topology" viewBox="0 0 700 560"></svg></section><section class="panel"><button onclick="resetTwin()">Reset replay</button><h3>Recent anomaly events</h3><table><thead><tr><th>t</th><th>Node</th><th>Metric</th><th>Score</th></tr></thead><tbody id="feed"></tbody></table></section></div></main>
<script>
let source; async function resetTwin(){if(source)source.close();await fetch('/live/reset',{method:'POST'});connect()}
function draw(s){time.textContent=s.timestamp_s+' / '+s.duration_s+' s';events.textContent=s.anomaly_count;active.textContent=s.active_anomaly_count;
const svg=document.getElementById('topology'), byId=Object.fromEntries(s.nodes.map(n=>[n.node_id,n]));let html='';
const links=window.topologyLinks||[];for(const l of links){const a=byId[l.source],b=byId[l.target];html+=`<line class="link" x1="${350+a.x*270}" y1="${280-a.y*250}" x2="${350+b.x*270}" y2="${280-b.y*250}"/>`}
for(const n of s.nodes){const x=350+n.x*270,y=280-n.y*250,r=n.role==='core'?13:n.role==='aggregation'?10:7;html+=`<circle class="node ${n.role} ${n.status==='anomaly'?'anomaly':''}" cx="${x}" cy="${y}" r="${r}"><title>${n.node_id}${n.telemetry?' · '+n.telemetry.latency_ms.toFixed(1)+' ms':''}</title></circle>`}svg.innerHTML=html;
feed.innerHTML=s.recent_events.slice().reverse().map(e=>`<tr><td>${e.timestamp_s}</td><td>${e.node_id}</td><td>${e.metric}</td><td>${e.score.toFixed(1)}</td></tr>`).join('')}
async function connect(){const t=await fetch('/topology').then(r=>r.json());window.topologyLinks=t.links;source=new EventSource('/live/stream?interval_ms=80');source.onmessage=e=>draw(JSON.parse(e.data));source.onerror=()=>source.close()}
connect();
</script></body></html>"""
