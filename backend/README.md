# Mandi Lens backend

## Setup

```bash
uv sync
cp .env.example .env
uv run fastapi dev app.main:app
```

Set `SARVAM_API_KEY` in `.env`. The frontend never receives this key. The
backend uses the installed `sarvamai` SDK for Document Intelligence, Saaras
speech-to-text, and Bulbul text-to-speech. `saaras:v4` supports crop-name
keyterms; use `SAARAS:v3` only if that model is enabled for your account.
Bulbul defaults to `bulbul:v3` with the `shubh` speaker.

The standalone chat smoke test uses the documented
`sarvam-105b-conversations` model:

```bash
uv run python sarvam_chat.py
```

It requires `SARVAM_API_KEY` in `.env` and never prints the key.

## Tests

```bash
uv run pytest
```

The deterministic comparison and price parser tests do not require a provider
key or network access.
