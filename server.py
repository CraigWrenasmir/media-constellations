#!/usr/bin/env python3
"""
Media Constellations — local backend.

Serves the single-page front-end and exposes /api/analyze, which:
  1. pulls a transcript for a YouTube link (or accepts pasted transcript text),
  2. runs `claude -p` (Claude Code headless) on your Max plan to generate a
     constellation in the exact schema the visualiser expects,
  3. returns it as JSON.

No API key required — it drives your authenticated Claude Code CLI, the same
way Surgipelago does. Run it on your own machine:

    ./.venv/bin/python server.py
    open http://127.0.0.1:5050
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

HERE = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=None)

# Which model claude -p uses. Sonnet gives noticeably richer constellations;
# set CONSTELLATION_MODEL=haiku to conserve your Max usage.
MODEL = os.environ.get("CONSTELLATION_MODEL", "sonnet")
MAX_TRANSCRIPT_WORDS = 14000

# Palette the front-end understands (assigned here so Claude focuses on content).
PALETTE = ["#46d6c4", "#b48bff", "#ffc06a", "#ff7fa8", "#7ce0a0", "#6fa8ff", "#e7c98a"]


# ----------------------------------------------------------------------------- transcript
def video_id(url: str):
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})", url or "")
    return m.group(1) if m else (url if re.fullmatch(r"[\w-]{11}", url or "") else None)


def fetch_transcript(vid: str):
    """Return plain-text transcript or None. Tries the API lib, then yt-dlp captions."""
    # 1. youtube-transcript-api (handle both old classmethod and new instance API)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        langs = ["en", "en-US", "en-GB"]
        if hasattr(YouTubeTranscriptApi, "get_transcript"):          # <=0.6.x
            chunks = YouTubeTranscriptApi.get_transcript(vid, languages=langs)
            text = " ".join(c["text"] for c in chunks if c.get("text"))
        else:                                                         # >=1.0
            fetched = YouTubeTranscriptApi().fetch(vid, languages=langs)
            text = " ".join(s.text for s in fetched if getattr(s, "text", ""))
        if text.strip():
            return clean(text)
    except Exception as e:
        print(f"[transcript] api lib failed: {e}", file=sys.stderr)

    # 2. yt-dlp auto/manual captions -> vtt -> text
    try:
        import tempfile, glob
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(
                ["yt-dlp", "--skip-download", "--write-auto-sub", "--write-sub",
                 "--sub-lang", "en.*", "--sub-format", "vtt",
                 "-o", os.path.join(td, "cap"), f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, timeout=90,
            )
            for vtt in glob.glob(os.path.join(td, "*.vtt")):
                return clean(vtt_to_text(Path(vtt).read_text(encoding="utf-8", errors="ignore")))
    except Exception as e:
        print(f"[transcript] yt-dlp failed: {e}", file=sys.stderr)
    return None


def vtt_to_text(vtt: str):
    out = []
    for line in vtt.splitlines():
        line = line.strip()
        if (not line or line.startswith("WEBVTT") or "-->" in line
                or line.isdigit() or line.startswith(("Kind:", "Language:"))):
            continue
        line = re.sub(r"<[^>]+>", "", line)  # strip inline timing tags
        if line and (not out or out[-1] != line):
            out.append(line)
    return " ".join(out)


def clean(text: str):
    text = re.sub(r"\[[^\]]*\]", " ", text)          # [Music], [Applause]
    text = re.sub(r"\s+", " ", text).strip()
    words = text.split()
    if len(words) > MAX_TRANSCRIPT_WORDS:
        text = " ".join(words[:MAX_TRANSCRIPT_WORDS]) + " …[transcript truncated]"
    return text


def fetch_meta(vid: str):
    try:
        r = subprocess.run(
            ["yt-dlp", "--skip-download", "--no-warnings",
             "--print", "%(title)s|||%(uploader)s|||%(duration_string)s",
             f"https://www.youtube.com/watch?v={vid}"],
            capture_output=True, text=True, timeout=45,
        )
        if r.returncode == 0 and "|||" in r.stdout:
            title, uploader, dur = (r.stdout.strip().split("|||") + ["", "", ""])[:3]
            return {"title": title, "uploader": uploader, "duration": dur}
    except Exception as e:
        print(f"[meta] failed: {e}", file=sys.stderr)
    return {"title": "", "uploader": "", "duration": ""}


# ----------------------------------------------------------------------------- the prompt
SCHEMA = """{
  "title": "...", "speaker": "...",
  "sub": "venue · year · length · type",
  "blurb": "one sentence capturing the essence, or a short pull-quote",
  "analysis": {
    "happening": "1-2 neutral sentences on what the media is doing",
    "assumptions": ["3 hidden premises it rests on"],
    "tensions": ["3 internal contradictions or tensions"],
    "absent": ["3 perspectives missing from the media"],
    "questions": ["3 questions worth asking"]
  },
  "echoes": [{"yr": "1901", "t": "short title", "p": "one-sentence historical resonance"}],
  "themes": [{
    "label": "theme name",
    "emotion": ["2 emotional patterns it works on"],
    "rhetoric": ["2 rhetorical moves it uses"],
    "readings": [{"lens": "tradition name", "p": "one-sentence interpretation"}],
    "thinkers": [{
      "name": "Thinker Name", "match": 88, "trad": "their tradition",
      "why": "one sentence on why they illuminate THIS media",
      "books": [{"t": "Book Title", "y": 1979, "c": "2-4 word concept"}],
      "concepts": ["2-3 concepts"]
    }]
  }],
  "missing": [{"label": "perspective", "why": "one sentence on what it would add"}],
  "praxis": {
    "reflective": [{"t": "an action", "s": "one-line how"}],
    "educational": [{"t": "", "s": ""}],
    "community": [{"t": "", "s": ""}],
    "civic": [{"t": "", "s": ""}],
    "creative": [{"t": "", "s": ""}],
    "organising": [{"t": "", "s": ""}],
    "personas": [{"n": "thinker or tradition", "l": "2-3 word lens", "p": "one-sentence invitation to act in their spirit"}]
  }
}"""

PROMPT = """You are the reasoning engine of "Media Constellations", a tool that turns a piece of media into a multi-perspective constellation of ideas. Your job is NOT to tell anyone what to think — it is to increase the number of perspectives, intellectual traditions, historical parallels and constructive responses a viewer can hold at once.

You are given a video's metadata and transcript. Produce ONE JSON object — and nothing else, no markdown fences, no commentary — matching EXACTLY this schema:

{schema}

PRINCIPLES — follow them strictly:
- Reason THROUGH an intellectual graph, not a list of famous names. Choose thinkers whose concepts genuinely illuminate THIS specific media, grounded in what it actually says. Avoid quote-machine name-dropping.
- Produce 4 to 6 themes. Each theme MUST have a "readings" array of exactly 3 COMPETING interpretations from genuinely different traditions (e.g. left / liberal / conservative, or materialist / idealist / postcolonial). STEELMAN each one — the strongest, most intelligent version, never a strawman. The tool must never collapse into a single interpretation.
- Each theme has exactly 3 thinkers. "match" is an integer 60-96 for relevance to THIS media. 1-2 books each, "y" an integer year (negative for BCE). 2-3 concepts each.
- "echoes": 3-4 historical parallels offered as RESONANCE, NOT EQUIVALENCE.
- "missing": 3-4 perspectives the media itself did not consider.
- "praxis": constructive responses — what can be DONE, in the spirit of expanded agency, NEVER who to attack. Two items per mode.
- Be even-handed and intellectually serious across the whole political and philosophical spectrum. If the media is politically charged, represent ITS OWN view at its strongest AND its critics at their strongest. Do not editorialise.
- Do NOT include any colours or ids — the application assigns those.

Output ONLY the JSON object.

=== MEDIA METADATA ===
{meta}

=== TRANSCRIPT ===
{transcript}
"""


def run_claude(prompt: str):
    """Drive claude -p on the Max plan; return parsed constellation dict."""
    proc = subprocess.run(
        ["claude", "-p", "--model", MODEL, "--output-format", "json"],
        input=prompt, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude exited {proc.returncode}: {proc.stderr[:400]}")
    # --output-format json wraps the reply: {"result": "<text>", ...}
    try:
        wrapper = json.loads(proc.stdout)
        text = wrapper.get("result", proc.stdout)
    except json.JSONDecodeError:
        text = proc.stdout
    return json.loads(extract_json(text))


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in model output")
    depth, instr, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        else:
            if ch == '"':
                instr = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    raise ValueError("unbalanced JSON object in model output")


def colourise(c: dict):
    """Inject palette colours + theme ids the front-end expects."""
    for i, th in enumerate(c.get("themes", [])):
        th["id"] = f"t{i}"
        th["color"] = PALETTE[i % len(PALETTE)]
        for j, rd in enumerate(th.get("readings", [])):
            rd["color"] = PALETTE[(i + j + 2) % len(PALETTE)]
    for i, mm in enumerate(c.get("missing", [])):
        mm["color"] = PALETTE[(i + 3) % len(PALETTE)]
    return c


# ----------------------------------------------------------------------------- routes
@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True) or {}
    url = (data.get("url") or "").strip()
    pasted = (data.get("transcript") or "").strip()
    vid = data.get("videoId") or video_id(url)
    if not vid:
        return jsonify(ok=False, error="That doesn't look like a YouTube link."), 400

    meta = fetch_meta(vid)
    transcript = clean(pasted) if pasted else fetch_transcript(vid)
    if not transcript or len(transcript.split()) < 30:
        return jsonify(
            ok=False, needTranscript=True,
            error="No captions found for this video. Paste the transcript text and try again."
        ), 422

    meta_str = (f'title: {meta["title"] or "(unknown)"}\n'
                f'channel/speaker: {meta["uploader"] or "(unknown)"}\n'
                f'duration: {meta["duration"] or "(unknown)"}\n'
                f'url: https://www.youtube.com/watch?v={vid}')
    prompt = PROMPT.format(schema=SCHEMA, meta=meta_str, transcript=transcript)

    try:
        constellation = colourise(run_claude(prompt))
    except subprocess.TimeoutExpired:
        return jsonify(ok=False, error="Claude took too long (over 10 min). Try a shorter video, or set CONSTELLATION_MODEL=haiku for faster runs."), 504
    except Exception as e:
        print(f"[analyze] {e}", file=sys.stderr)
        return jsonify(ok=False, error=f"Could not build the constellation: {e}"), 500

    constellation["yt"] = vid
    constellation.setdefault("speaker", meta["uploader"] or "")
    return jsonify(ok=True, constellation=constellation, model=MODEL)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    print(f"\n  Media Constellations  →  http://127.0.0.1:{port}")
    print(f"  model: {MODEL} (set CONSTELLATION_MODEL=haiku to conserve Max usage)\n")
    app.run(host="127.0.0.1", port=port, debug=False)
