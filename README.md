# Jev API Usage Dashboard 💰

Interactive Streamlit dashboard that tracks every call, token, and dollar spent on the [Jev](https://typesafe.ai) decision-making API.

Built by Yi-Che Hsieh (TYC-000) using Streamlit + Plotly.

![dashboard preview](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)

## Features

- **Real-time tracking** of all Jev API calls (cached for 5 min)
- **Interactive charts** powered by Plotly (zoom, hover, filter)
- **Cost analytics** by day, by script, by token bucket
- **Credit tracking** against your $5 TypeSafe early-access credit
- **Privacy-first** — API key never leaves your machine

## Live demo

🔗 https://share.streamlit.io/TYC-000/jev-dashboard

## Run locally

```bash
pip install -r requirements.txt
streamlit run jev_dashboard.py
```

Place your `jev_usage.jsonl` in `data/` (one JSON object per line, with `ts`, `script`, `section`, `input_tokens`, `cost_usd`).

## Data format

Each line in `data/jev_usage.jsonl` is a JSON object:

```json
{"ts": "2026-09-24T10:30:00", "script": "lit_manager.py", "section": "evaluate_paper", "input_tokens": 900, "output_tokens": 112, "cost_usd": 0.0000378}
```

## License

MIT
