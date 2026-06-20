"""Pre-generate a few constellations on Max for the static showcase."""
import json, sys, concurrent.futures
import server

IDS = ["D9Ihs241zeg", "iG9CE55wbtY", "TMrtLsQbaok"]  # Adichie, Robinson, Greta

def one(vid):
    cf = server.CACHE_DIR / f"{vid}.json"
    if cf.exists():
        return f"{vid}: already cached"
    try:
        meta = server.fetch_meta(vid)
        tr = server.fetch_transcript(vid)
        if not tr:
            return f"{vid}: NO TRANSCRIPT"
        meta_str = (f'title: {meta["title"] or "(unknown)"}\n'
                    f'channel/speaker: {meta["uploader"] or "(unknown)"}\n'
                    f'duration: {meta["duration"] or "(unknown)"}\n'
                    f'url: https://www.youtube.com/watch?v={vid}')
        block = f"=== MEDIA METADATA ===\n{meta_str}\n\n=== TRANSCRIPT ===\n{tr}"
        c = server.colourise(server.generate(block))
        c["yt"] = vid
        c.setdefault("speaker", meta["uploader"] or "")
        cf.write_text(json.dumps(c, indent=2))
        return f"{vid}: OK — {len(c['themes'])} themes — {c.get('title','')[:40]}"
    except Exception as e:
        return f"{vid}: ERROR {e}"

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    for r in ex.map(one, IDS):
        print(r, flush=True)
print("done", flush=True)
