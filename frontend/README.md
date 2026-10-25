# Mandi Lens frontend

## Setup

```bash
npm install
npm run dev
```

The app expects the FastAPI backend at `http://localhost:8000/api`. Set
`VITE_API_URL` when the backend is hosted elsewhere.

```bash
npm run build
npm run lint
```

The successful path is designed for a mobile browser: capture a board image,
confirm the extracted crop and price, record the offer, confirm the recognized
price, and review/replay the comparison. OCR and speech failures remain
recoverable through manual numeric entry.
