# Mandi Lens

Mandi Lens is a mobile-first web application that helps Indian farmers
understand whether a middleman's offer is lower than a price shown on a mandi
board.

## The problem

Mandi price boards can be difficult to read quickly, especially when they use
English, unfamiliar scripts, multiple crops, or several price columns. This
information gap can make it difficult for a farmer to compare the board price
with the price offered by a middleman.

Mandi Lens is designed for the practical situation at the market:

- The farmer may not want to type during the normal flow.
- The board may contain several crops and min/max/modal prices.
- OCR or speech recognition may be uncertain.
- A failed AI service must not leave the farmer without a way to continue.

Mandi Lens compares only the prices supplied by the board and the farmer. It
does not claim that the board price is a guaranteed fair price or that a
difference proves exploitation.

## The solution

The application turns a board photograph and a spoken offer into a simple
comparison:

1. The farmer photographs or uploads a mandi board.
2. Sarvam Vision extracts the crop names and listed prices.
3. The farmer selects or types the crop name.
4. Mandi Lens automatically uses the corresponding OCR price; the farmer does
   not retype the board price during the normal flow.
5. The farmer speaks the middleman's offer or enters it manually.
6. Saaras transcribes the offer and extracts the price.
7. The farmer confirms or corrects the recognized offer.
8. The app calculates the difference and percentage.
9. Bulbul speaks the result in Hindi or Tamil, with a replay option.

Manual entry is available only as a recovery path when OCR or speech
recognition cannot produce a usable result.

## Features

- Mobile-first React and TypeScript interface.
- Hindi and Tamil localization.
- Camera capture and image upload.
- Structured crop and min/max/modal price extraction.
- Crop-name selection and search.
- Browser microphone recording with `MediaRecorder`.
- Saaras speech-to-text with crop-name keyterms.
- Manual correction for uncertain speech recognition.
- Deterministic price comparison:
  - `difference = board_price - offered_price`
  - percentage is calculated only when the board price is greater than zero.
- Bulbul text-to-speech with automatic playback attempt and replay fallback.
- Backend-only Sarvam API access.
- No accounts, user profiles, price history, or persistent farmer data.

## Architecture

```text
React + TypeScript + Vite + Tailwind CSS
                |
                v
        FastAPI backend
                |
                v
 Sarvam Document AI / Saaras / Bulbul
```

All Sarvam credentials remain in the backend. The browser never receives the
Sarvam API key.

## Project structure

```text
backend/
  app/
    api.py                 # HTTP endpoints
    main.py                # FastAPI application
    schemas.py             # Request and response models
    core/config.py         # Environment configuration
    services/
      comparison.py        # Deterministic price comparison
      price_parser.py      # Speech price extraction
      sarvam.py            # Sarvam SDK adapters and OCR normalization
  tests/                   # Backend tests
  sarvam_chat.py           # Separate Sarvam chat smoke test

frontend/
  src/App.tsx              # Four-step farmer workflow
  src/index.css            # Responsive visual design
```

## Requirements

- Python 3.13 or a compatible Python version supported by the backend project.
- [`uv`](https://docs.astral.sh/uv/).
- Node.js and npm.
- A Sarvam API key for OCR, speech, and text-to-speech.
- A browser that supports camera access, microphone access, and
  `MediaRecorder`.

## Configuration

From the backend directory:

```bash
cp .env.example .env
```

Set the key in `backend/.env`:

```dotenv
SARVAM_API_KEY=your_key_here
FRONTEND_ORIGINS=["http://localhost:5173"]
SARVAM_SPEECH_MODEL=saaras:v4
SARVAM_TTS_MODEL=bulbul:v3
REQUEST_TIMEOUT_SECONDS=120
```

Do not commit `.env` or place the Sarvam key in frontend environment variables.

The backend uses the installed `sarvamai` SDK:

- Document AI Extract for structured board crop/price extraction.
- Saaras `saaras:v4` for speech-to-text.
- Bulbul `bulbul:v3` for speech synthesis.

Model availability and pricing depend on the Sarvam account. Check Sarvam's
current documentation if a model is unavailable for the account.

## Run locally

Start the backend:

```bash
cd backend
uv sync
uv run fastapi dev app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally
`http://localhost:5173`.

If the backend is hosted at another URL, set this before starting the
frontend:

```bash
VITE_API_URL=http://localhost:8000/api npm run dev
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health check |
| `POST` | `/api/ocr` | Extract crop and price records from an image |
| `POST` | `/api/speech/transcribe` | Transcribe a recorded offer |
| `POST` | `/api/speech/synthesize` | Generate result speech |
| `POST` | `/api/comparison` | Calculate the deterministic price comparison |

## Testing

Backend tests do not require a real Sarvam request:

```bash
cd backend
uv run pytest
```

Frontend checks:

```bash
cd frontend
npm run build
npm run lint
```

## Failure recovery

The core comparison remains available when AI services fail:

- Unreadable board: enter the crop and board price manually.
- Missing or ambiguous speech price: type the offer manually.
- Microphone permission denied: use manual offer entry.
- TTS failure or blocked autoplay: use **Listen Again** or read the visual
  comparison.
- Backend/provider failure: the UI displays a recoverable error instead of
  silently fabricating a result.

Uploaded images and recorded audio are processed in memory or through
temporary provider operations. The MVP does not intentionally persist farmer
audio, images, accounts, or price history.

## Scope and limitations

This is an MVP intended for local demonstration and iterative field testing.
OCR accuracy depends on image quality, board layout, language, and provider
availability. Validate the application with representative mandi boards before
using it in a production setting.

Production deployment should use HTTPS, a restricted CORS origin, secure
secret management, provider usage monitoring, and additional observability.
