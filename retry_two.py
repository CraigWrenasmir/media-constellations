import json, subprocess, server

for vid in ["-d7oR0J9usQ", "pPKDq_6iKLY"]:
    cf = server.CACHE_DIR / f"{vid}.json"
    if cf.exists():
        print(vid, "already cached", flush=True); continue
    meta = server.fetch_meta(vid)
    tr = server.fetch_transcript(vid)
    meta_str = (f'title: {meta["title"] or "(unknown)"}\n'
                f'channel/speaker: {meta["uploader"] or "(unknown)"}\n'
                f'duration: {meta["duration"] or "(unknown)"}\n'
                f'url: https://www.youtube.com/watch?v={vid}')
    block = f"=== MEDIA METADATA ===\n{meta_str}\n\n=== TRANSCRIPT ===\n{tr}"
    full = server.INSTRUCTIONS + "\n\n" + block
    print(vid, "generating…", flush=True)
    proc = subprocess.run(["claude", "-p", "--model", "sonnet", "--output-format", "json"],
                          input=full, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        print(vid, "CLAUDE ERR", proc.stderr[:300], flush=True); continue
    try:
        text = json.loads(proc.stdout).get("result", proc.stdout)
    except json.JSONDecodeError:
        text = proc.stdout
    try:
        c = json.loads(server.extract_json(text))
    except Exception as e:
        print(vid, "PARSE FAIL", e, "| RAW:", text[:300], flush=True); continue
    if "themes" not in c:
        print(vid, "NO THEMES keys=", list(c.keys()), "| RAW:", text[:300], flush=True); continue
    c = server.colourise(c); c["yt"] = vid; c.setdefault("speaker", meta["uploader"] or "")
    cf.write_text(json.dumps(c, indent=2))
    print(vid, "OK —", len(c["themes"]), "themes —", c.get("title", "")[:45], flush=True)
print("done", flush=True)
