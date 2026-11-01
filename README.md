# Paper Summarizer 📄

An AI-powered tool that extracts key insights from academic papers with one click. Upload a PDF and get structured summaries in seconds.

## Features

- 📤 **One-click upload** - Drag & drop your PDF
- 🧠 **AI-powered analysis** - NVIDIA LLM powered
- 🌐 **Bilingual support** - Chinese & English output
- 📊 **Structured output** - JSON, Markdown, or HTML
- 🔍 **Key elements extracted**:
  - Title & Authors
  - Abstract summary
  - Research objectives
  - Methods overview
  - Key findings
  - Conclusions

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Set your NVIDIA API key as environment variable:
```bash
export NVIDIA_API_KEY="nvapi-xxxxx"
```

Or use OpenAI compatible API:
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.some-service.com/v1"
```

## API

```bash
# Start the API server
python api.py  # runs on http://localhost:8000

# Test it
curl -X POST http://localhost:8000/summarize \
  -F "file=@paper.pdf" \
  -F "language=zh" \
  -F "format=markdown"
```

## Output Formats

- **JSON**: Machine-readable for integrations
- **Markdown**: Human-readable, easy to share
- **HTML**: Beautiful formatted report

## Use Cases

- Literature review acceleration
- Research paper screening
- Meeting preparation (know the paper before reading)
- Teaching material preparation

## License

MIT License - Free to use and modify.
