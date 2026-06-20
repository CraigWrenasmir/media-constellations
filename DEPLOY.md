# Deploying Media Constellations (public, OpenAI-powered)

The hosted version swaps the local `claude -p` engine for the **OpenAI API**, so
anyone can map any video without your Mac being involved. Locally it still falls
back to `claude -p` on Max whenever `OPENAI_API_KEY` is *not* set — so nothing
changes about your local workflow.

## 1. Get an OpenAI API key
This is separate from any ChatGPT subscription.
1. Go to <https://platform.openai.com> → **API keys** → create a key.
2. Add a little credit under **Billing** (a few dollars covers a lot of testing).
3. Note a model id under **Models** (e.g. `gpt-5.4-mini`). You'll set this as `OPENAI_MODEL`.

## 2. Push the repo to GitHub
```bash
cd ~/Media-Constellations
gh repo create media-constellations --private --source=. --push   # or via the GitHub UI
```
`cache/`, `.venv/` and secrets are already git-ignored.

## 3. Deploy on Render (simplest with long request timeouts)
1. <https://render.com> → **New → Web Service** → connect the repo.
2. Settings:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn server:app --bind 0.0.0.0:$PORT --timeout 300 --workers 2`
3. **Environment variables:**
   - `OPENAI_API_KEY` = your key
   - `OPENAI_MODEL` = e.g. `gpt-5.4-mini`
4. Deploy → you get a public `https://…onrender.com` link to share.

(Heroku works the same way — the included `Procfile` already has the right start
command; set the two env vars with `heroku config:set`.)

## 4. Share the link
Send the URL to your testers. The first time someone maps a given video it calls
OpenAI (takes ~30–90s); after that it's cached and instant for everyone.

---

## Two honest caveats for the hosted version

**Transcripts on cloud IPs.** YouTube often blocks automated transcript fetching
from datacenter IP ranges ("Sign in to confirm you're not a bot"). When that
happens the tool already falls back to a **"paste the transcript" box**, which
always works. If you want reliable auto-fetch in the cloud, add a residential
proxy (youtube-transcript-api supports one) — ask me and I'll wire it in. The
**"Play here"** local-stream button (yt-dlp) is also unreliable on cloud IPs; the
embed + "Watch on YouTube" links remain.

**Cost.** Each fresh map is one API call over a transcript (~15–25k input tokens)
plus a few thousand output tokens. On a `mini`-class model that's roughly a few
cents per video; on a full GPT-5-class model, more. Caching means you only pay
once per video, ever. Check current pricing at <https://openai.com/api/pricing>.

**Caching note.** The on-disk cache lives on the host's filesystem, which most
platforms wipe on redeploy/restart. Fine for testing; if you want durable caching
later, we can move it to a small database or object store.
