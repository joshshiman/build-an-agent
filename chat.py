#!/usr/bin/env python3
"""
chat.py — a tiny web chat for your watsonx Orchestrate agent.

What it does:
  * Serves a small chat page at http://localhost:3000
  * Talks to watsonx Orchestrate for you (using the URL + key in your .env)

Why a server file (and not just an HTML page):
  Your browser is not allowed to call Orchestrate directly, and your API key
  must never live in a web page. So this file runs on your machine, keeps the
  key safe, swaps it for a short-lived token, and relays your messages.

Run it:
    python chat.py          (Windows: py chat.py)
Then open http://localhost:3000 in your browser.

It reads two values from the .env file you already made:
    WXO_URL       your instructor's Orchestrate instance URL
    WXO_API_KEY   your instructor's API key
"""

import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 3000
IAM_URL = "https://iam.cloud.ibm.com/identity/token"

# ----------------------------------------------------------------------------
# Read .env (same file you created earlier in the workshop)
# ----------------------------------------------------------------------------
def load_env(path=".env"):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env

ENV = load_env()
WXO_URL = (ENV.get("WXO_URL") or os.environ.get("WXO_URL") or "").rstrip("/")
WXO_API_KEY = ENV.get("WXO_API_KEY") or os.environ.get("WXO_API_KEY") or ""

if not WXO_URL or not WXO_API_KEY:
    print("\n  Could not find WXO_URL and WXO_API_KEY.")
    print("  Make sure you run this from your project folder (the one with the .env file),")
    print("  and that .env contains both WXO_URL and WXO_API_KEY.\n")
    sys.exit(1)

# Some corporate networks use custom certificates. Default verification is used;
# if you hit an SSL error at the workshop, ask a helper.
SSL_CTX = ssl.create_default_context()

# ----------------------------------------------------------------------------
# Auth: swap the API key for a short-lived bearer token (cached, auto-refreshed)
# ----------------------------------------------------------------------------
_token = {"value": None, "expires": 0}

def get_token():
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": WXO_API_KEY,
    }).encode()
    req = urllib.request.Request(
        IAM_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as r:
        body = json.loads(r.read())
    _token["value"] = body["access_token"]
    _token["expires"] = time.time() + int(body.get("expires_in", 3600))
    return _token["value"]

def api(method, path, payload=None):
    url = f"{WXO_URL}{path}"
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/json",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=120) as r:
        return json.loads(r.read())

# ----------------------------------------------------------------------------
# Orchestrate calls
# ----------------------------------------------------------------------------
def list_agents():
    data = api("GET", "/v1/orchestrate/agents")
    agents = data.get("agents", data) if isinstance(data, dict) else data
    out = []
    for a in agents or []:
        aid = a.get("id") or a.get("agent_id")
        name = a.get("display_name") or a.get("name") or aid
        if aid:
            out.append({"id": aid, "name": name})
    return out

def send_message(agent_id, content, thread_id=None):
    payload = {"message": {"role": "user", "content": content}, "agent_id": agent_id}
    if thread_id:
        payload["thread_id"] = thread_id
    started = api("POST", "/v1/orchestrate/runs", payload)
    run_id = started.get("run_id") or started.get("id")
    thread_id = started.get("thread_id", thread_id)
    if not run_id:
        # Some responses return the message inline; try to read it.
        return extract_text(started), thread_id

    # Poll until the run finishes.
    deadline = time.time() + 110
    while time.time() < deadline:
        run = api("GET", f"/v1/orchestrate/runs/{run_id}")
        status = run.get("status", "")
        if status in ("completed", "succeeded"):
            return extract_text(run), run.get("thread_id", thread_id)
        if status in ("failed", "cancelled"):
            err = run.get("last_error") or "The agent run did not complete."
            return f"(Sorry — {err})", thread_id
        time.sleep(0.9)
    return "(The agent took too long to respond. Please try again.)", thread_id

def extract_text(obj):
    """Pull the assistant's plain text out of a run/message response."""
    msg = None
    if isinstance(obj, dict):
        result = obj.get("result", {})
        if isinstance(result, dict):
            msg = result.get("data", {}).get("message")
        msg = msg or obj.get("message")
    if not msg:
        return "(No reply received.)"
    content = msg.get("content", msg)
    if isinstance(content, str):
        return content
    parts = []
    if isinstance(content, list):
        for c in content:
            if isinstance(c, dict) and c.get("text"):
                parts.append(c["text"])
            elif isinstance(c, str):
                parts.append(c)
    return "\n".join(parts).strip() or "(No reply received.)"

# ----------------------------------------------------------------------------
# The web page (Carbon-styled, self-contained)
# ----------------------------------------------------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Your Orchestrate Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono&display=swap" rel="stylesheet">
<style>
  :root{
    --blue:#0f62fe; --blue-hover:#0353e9;
    --ink:#161616; --ink-2:#525252; --line:#e0e0e0;
    --bg:#ffffff; --layer:#f4f4f4; --layer-2:#e8e8e8;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; background:var(--layer); color:var(--ink);
    font-family:'IBM Plex Sans',system-ui,sans-serif;
    display:flex; align-items:center; justify-content:center;
  }
  .app{
    width:100%; max-width:720px; height:100vh; max-height:900px;
    background:var(--bg); display:flex; flex-direction:column;
    border:1px solid var(--line);
  }
  header{
    background:var(--ink); color:#fff; padding:16px 20px;
    display:flex; align-items:center; gap:12px; flex:0 0 auto;
  }
  header .dot{width:10px;height:10px;border-radius:50%;background:#42be65;flex:0 0 auto}
  header h1{font-size:16px; font-weight:600; margin:0; letter-spacing:.01em}
  header .sub{font-size:12px; color:#c6c6c6; margin-top:2px}
  .bar{
    display:flex; align-items:center; gap:10px; padding:10px 20px;
    background:var(--layer); border-bottom:1px solid var(--line); flex:0 0 auto;
  }
  .bar label{font-size:12px; color:var(--ink-2); font-weight:500}
  select{
    font-family:inherit; font-size:13px; color:var(--ink);
    background:var(--bg); border:1px solid var(--line);
    border-bottom:1px solid var(--ink-2);
    padding:6px 10px; min-width:220px; cursor:pointer;
  }
  select:focus{outline:2px solid var(--blue); outline-offset:-2px}
  #log{flex:1 1 auto; overflow-y:auto; padding:24px 20px; display:flex; flex-direction:column; gap:16px}
  .row{display:flex; gap:10px; max-width:100%}
  .row.user{flex-direction:row-reverse}
  .avatar{
    width:28px;height:28px;border-radius:50%;flex:0 0 auto;
    display:flex;align-items:center;justify-content:center;
    font-size:12px;font-weight:600;color:#fff;
  }
  .row.agent .avatar{background:var(--blue)}
  .row.user .avatar{background:var(--ink-2)}
  .bubble{
    padding:12px 14px; border-radius:12px; font-size:14px; line-height:1.5;
    max-width:78%; white-space:pre-wrap; word-wrap:break-word;
  }
  .row.agent .bubble{background:var(--layer); color:var(--ink); border-top-left-radius:3px}
  .row.user .bubble{background:var(--blue); color:#fff; border-top-right-radius:3px}
  .chips{display:flex; flex-wrap:wrap; gap:8px; padding:0 20px 12px}
  .chip{
    font-family:inherit; font-size:13px; color:var(--blue);
    background:var(--bg); border:1px solid var(--blue);
    padding:6px 12px; border-radius:20px; cursor:pointer;
  }
  .chip:hover{background:#edf5ff}
  form{display:flex; gap:0; border-top:1px solid var(--line); flex:0 0 auto}
  #msg{
    flex:1 1 auto; font-family:inherit; font-size:14px; color:var(--ink);
    border:none; padding:16px 20px; resize:none; height:56px;
  }
  #msg:focus{outline:2px solid var(--blue); outline-offset:-2px}
  #send{
    flex:0 0 auto; border:none; background:var(--blue); color:#fff;
    font-family:inherit; font-size:14px; font-weight:500; padding:0 22px; cursor:pointer;
  }
  #send:hover{background:var(--blue-hover)}
  #send:disabled{background:var(--layer-2); color:var(--ink-2); cursor:default}
  .typing{display:flex; gap:4px; padding:4px 2px}
  .typing span{width:7px;height:7px;border-radius:50%;background:var(--ink-2);opacity:.4;animation:b 1.2s infinite}
  .typing span:nth-child(2){animation-delay:.2s}
  .typing span:nth-child(3){animation-delay:.4s}
  @keyframes b{0%,60%,100%{opacity:.3;transform:translateY(0)}30%{opacity:1;transform:translateY(-3px)}}
  .err{color:#da1e28; font-size:13px; text-align:center; padding:8px}
</style>
</head>
<body>
<div class="app">
  <header>
    <div class="dot"></div>
    <div>
      <h1>Your Orchestrate Agent</h1>
      <div class="sub">Built by you &middot; running on watsonx Orchestrate</div>
    </div>
  </header>
  <div class="bar">
    <label for="agent">Agent</label>
    <select id="agent"><option>Loading&hellip;</option></select>
  </div>
  <div id="log"></div>
  <div class="chips" id="chips"></div>
  <form id="form">
    <textarea id="msg" placeholder="Ask your agent something&hellip;" autocomplete="off"></textarea>
    <button id="send" type="submit">Send</button>
  </form>
</div>
<script>
  const log = document.getElementById('log');
  const form = document.getElementById('form');
  const msg = document.getElementById('msg');
  const send = document.getElementById('send');
  const agentSel = document.getElementById('agent');
  const chipsWrap = document.getElementById('chips');
  let threadId = null;

  const STARTERS = [
    "Plan a 40-person team offsite in Austin",
    "Estimate the budget for a 120-guest wedding",
    "Suggest venues in Chicago for 60 people under $8000",
  ];

  function bubble(role, text){
    const row = document.createElement('div');
    row.className = 'row ' + role;
    const av = document.createElement('div');
    av.className = 'avatar';
    av.textContent = role === 'user' ? 'You' : 'AI';
    const b = document.createElement('div');
    b.className = 'bubble';
    b.textContent = text;
    row.appendChild(av); row.appendChild(b);
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return b;
  }

  function typingBubble(){
    const row = document.createElement('div');
    row.className = 'row agent';
    row.innerHTML = '<div class="avatar">AI</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>';
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return row;
  }

  function showChips(){
    chipsWrap.innerHTML = '';
    STARTERS.forEach(s => {
      const c = document.createElement('button');
      c.className = 'chip'; c.type = 'button'; c.textContent = s;
      c.onclick = () => { msg.value = s; msg.focus(); };
      chipsWrap.appendChild(c);
    });
  }

  async function loadAgents(){
    try{
      const r = await fetch('/api/agents');
      const data = await r.json();
      agentSel.innerHTML = '';
      if(!data.agents || !data.agents.length){
        agentSel.innerHTML = '<option>No agents found</option>';
        return;
      }
      data.agents.forEach(a => {
        const o = document.createElement('option');
        o.value = a.id; o.textContent = a.name;
        agentSel.appendChild(o);
      });
    }catch(e){
      agentSel.innerHTML = '<option>Could not load agents</option>';
    }
  }

  async function ask(text){
    if(!text.trim()) return;
    threadId = threadId; // keep thread across turns
    bubble('user', text);
    msg.value=''; send.disabled = true; chipsWrap.innerHTML='';
    const typing = typingBubble();
    try{
      const r = await fetch('/api/chat', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({agent_id: agentSel.value, message: text, thread_id: threadId})
      });
      const data = await r.json();
      typing.remove();
      if(data.error){ const e=document.createElement('div'); e.className='err'; e.textContent=data.error; log.appendChild(e); }
      else { bubble('agent', data.reply); threadId = data.thread_id || threadId; }
    }catch(e){
      typing.remove();
      const el=document.createElement('div'); el.className='err'; el.textContent='Something went wrong. Is chat.py still running?'; log.appendChild(el);
    }
    send.disabled = false; log.scrollTop = log.scrollHeight; msg.focus();
  }

  form.addEventListener('submit', e => { e.preventDefault(); ask(msg.value); });
  msg.addEventListener('keydown', e => { if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); ask(msg.value);} });

  bubble('agent', "Hi! I'm your Event Planner agent. Tell me about the event you're planning, and I'll help with budgets, venues, and the guest list.");
  showChips();
  loadAgents();
  msg.focus();
</script>
</body>
</html>"""

# ----------------------------------------------------------------------------
# Web server
# ----------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body)
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # keep the terminal quiet

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/agents":
            try:
                return self._send(200, {"agents": list_agents()})
            except Exception as e:
                return self._send(200, {"agents": [], "error": str(e)})
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/chat":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            agent_id = req.get("agent_id")
            message = (req.get("message") or "").strip()
            thread_id = req.get("thread_id")
            if not agent_id or not message:
                return self._send(200, {"error": "Please pick an agent and type a message."})
            reply, thread_id = send_message(agent_id, message, thread_id)
            return self._send(200, {"reply": reply, "thread_id": thread_id})
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "ignore")[:300]
            return self._send(200, {"error": f"Orchestrate returned {e.code}. {detail}"})
        except Exception as e:
            return self._send(200, {"error": f"Something went wrong: {e}"})


def main():
    print("\n  Connecting to watsonx Orchestrate...")
    try:
        agents = list_agents()
        print(f"  Connected. Found {len(agents)} agent(s).")
    except Exception as e:
        print(f"  Warning: could not list agents yet ({e}).")
        print("  The page will still open; check your .env and network if agents don't appear.")
    print(f"\n  Chat is ready at:  http://localhost:{PORT}")
    print("  Press Ctrl+C to stop.\n")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped. See you next time!\n")


if __name__ == "__main__":
    main()
