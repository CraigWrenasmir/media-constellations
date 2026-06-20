# Media Constellations

Paste a YouTube link → it pulls the transcript and reasons through an intellectual
graph, then draws the result as a living constellation: the media at the centre,
themes orbiting it, thinkers orbiting each theme, competing readings, historical
echoes, missing perspectives, and constructive **praxis**.

Not a fact-checker or a philosophy-quote machine. A machine for increasing the
number of perspectives, parallels and constructive responses you can hold at once.
The north star: *can you see more perspectives after watching than before?*

## Running it

It runs **locally on your Mac** and powers the reasoning with **`claude -p`** on
your **Claude Max** plan — no API key, no per-token bill (same arrangement as
Surgipelago).

```bash
./run.sh
# then open http://127.0.0.1:5050
```

First run sets up a virtualenv and installs Flask + the transcript library.

### Options
- `CONSTELLATION_MODEL=haiku ./run.sh` — faster and lighter on Max usage (default is `sonnet`, which gives richer constellations but can take a minute or two on long videos).
- `PORT=8080 ./run.sh` — use a different port.
- **No captions?** The tool offers a box to paste the transcript text; it maps from that.

## How it's wired
- `index.html` — the whole front-end (constellation visualiser, contradiction engine, praxis dock, Atlas mode). No build step.
- `server.py` — local Flask app. Serves the page and exposes `/api/analyze`, which fetches the transcript (youtube-transcript-api → yt-dlp fallback) and runs `claude -p` to generate the constellation in the visualiser's schema.

## The honest boundary
Because it drives *your* authenticated Claude Code, the Max-powered version is a
tool **you run on your machine** — great for your own use, demos and the
walk-and-show. A public website for strangers would need the paid Anthropic API
instead of Max.
