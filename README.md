# Paper Summarizer 📄

AI-powered PDF paper summarizer — runs entirely in your browser, no server needed.

## Features

- 📤 **Drag & drop** PDF upload
- 🧠 **AI analysis** — extracts title, authors, abstract, objectives, methods, findings, conclusion
- 🌐 **Bilingual** — Chinese (zh) & English (en) output
- 🔒 **Privacy-first** — PDF text processed client-side, only sent to AI API
- 📦 **Zero deployment** — just open the HTML file or host on any static site

## Quick Start (Use Online)

1. Open [paper-summarizer.netlify.app](https://paper-summarizer.netlify.app) (or self-host, see below)
2. Drag & drop a PDF
3. Click "Summarize" — wait ~30-60 seconds
4. Download result as Markdown / JSON / HTML

## Self-Host (Free, 2 minutes)

This project has two parts:
- `index.html` — the frontend (host anywhere: GitHub Pages, Netlify, Vercel, etc.)
- `worker.js` — the API proxy (Cloudflare Workers, free tier)

### Step 1: Deploy the Worker

1. Go to [workers.cloudflare.com](https://workers.cloudflare.com)
2. Click "Create application" → "Hello World Worker"
3. Replace the code with `worker.js` from this repo
4. Go to Settings → Variables → Add:
   - `API_KEY` = your OpenRouter API key (`sk-or-...`)
   - (Optional) `MODEL` = `deepseek/deepseek-chat`
5. Click "Deploy"
6. Copy your worker URL (e.g., `https://your-name.workers.dev`)

### Step 2: Deploy the Frontend

Edit `index.html`, change line 215:
```javascript
const API_URL = 'https://your-name.workers.dev';
```

Then host `index.html` anywhere:
- GitHub Pages (add `index.html` to a repo, enable Pages)
- Netlify (drag & drop folder)
- Vercel
- Cloudflare Pages

### Or just use GitHub Pages

1. Fork this repo
2. Edit `index.html`, set `API_URL` to your worker
3. Enable GitHub Pages in repo settings
4. Done!

## How It Works

```
Browser (reads PDF) → Cloudflare Worker → OpenRouter API → JSON result
```

- PDF is read locally using **PDF.js** (no upload to any server)
- Only the extracted text is sent to the AI
- The Worker proxies requests to OpenRouter, hiding your API key
- Result is rendered and downloadable in 3 formats

## API Contract

```
POST /chat/completions
{
  "text": "extracted pdf text...",
  "language": "zh",      // or "en"
  "prompt": "optional custom prompt"
}
→ {
    "title": "...",
    "authors": [...],
    "abstract": "...",
    "objectives": [...],
    "methods": "...",
    "key_findings": [...],
    "conclusion": "...",
    "meta": {"language": "zh", "model": "...", "chars": 12345}
  }
```

## Tech Stack

- **Frontend**: Vanilla JS + PDF.js
- **Backend**: Cloudflare Workers (serverless)
- **AI**: OpenRouter (DeepSeek, GPT-4, Claude, etc.)
- **License**: MIT

## License

MIT — free to use, modify, and host.
