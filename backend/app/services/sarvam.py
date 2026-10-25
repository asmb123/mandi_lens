import asyncio
import base64
import json
import re
import time
from html.parser import HTMLParser
from typing import Any

from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

from app.core.config import Settings
from app.services.price_parser import extract_price


class SarvamError(RuntimeError):
    pass


def _client(settings: Settings) -> SarvamAI:
    if not settings.sarvam_api_key:
        raise SarvamError("Sarvam API key is not configured")
    return SarvamAI(api_subscription_key=settings.sarvam_api_key, timeout=settings.request_timeout_seconds)


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _provider_error(prefix: str, exc: ApiError) -> SarvamError:
    status_code = getattr(exc, "status_code", None)
    suffix = f" (provider status {status_code})" if status_code else ""
    body = getattr(exc, "body", None)
    detail = ""
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message") or error.get("detail")
            if code or message:
                detail = f": {code + ': ' if isinstance(code, str) else ''}{message}" if message else f": {code}"
        elif isinstance(error, str):
            detail = f": {error}"
    elif isinstance(body, str) and body.strip():
        detail = f": {body[:300]}"
    return SarvamError(f"{prefix}{suffix}{detail}")


def _vision_stage_error(stage: str, exc: Exception) -> SarvamError:
    if isinstance(exc, ApiError):
        return _provider_error(f"Vision {stage} failed", exc)
    return SarvamError(f"Vision {stage} failed: {type(exc).__name__}: {str(exc)[:300]}")


def _number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        match = re.search(r"\d[\d,]*", value)
        if match:
            parsed = int(match.group().replace(",", ""))
            return parsed if parsed >= 0 else None
    return None


def _normalize_document(text: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        columns = [column.strip() for column in line.strip().strip("|").split("|")]
        if len(columns) < 2 or all(set(column) <= {"-", ":"} for column in columns):
            continue
        crop = columns[0]
        if not crop or crop.lower() in {"crop", "commodity", "name", "फसल"}:
            continue
        numeric = [_number(column) for column in columns[1:]]
        numeric = [value for value in numeric if value is not None]
        if numeric:
            prices: dict[str, int | None] = {"min": None, "max": None, "modal": None}
            if len(numeric) == 1:
                prices["modal"] = numeric[0]
            elif len(numeric) == 2:
                prices["min"], prices["max"] = numeric
            else:
                prices["min"], prices["max"], prices["modal"] = numeric[:3]
            records.append({"crop_name": crop, "prices": prices, "source_text": line})
    if records:
        return records
    for line in text.splitlines():
        numbers = [int(value.replace(",", "")) for value in re.findall(r"(?<!\d)\d[\d,]*(?!\d)", line)]
        if not numbers:
            continue
        crop = re.sub(r"[₹\d,./:-]+", " ", line)
        crop = re.sub(r"\b(?:rs|inr|रुपये|रुपया|रूपये|रुपए)\b", " ", crop, flags=re.IGNORECASE)
        crop = " ".join(crop.split()).strip("| ")
        if not crop or crop.lower() in {"crop", "commodity", "name", "फसल"}:
            continue
        prices: dict[str, int | None] = {"min": None, "max": None, "modal": None}
        if len(numbers) == 1:
            prices["modal"] = numbers[0]
        elif len(numbers) == 2:
            prices["min"], prices["max"] = numbers
        else:
            prices["min"], prices["max"], prices["modal"] = numbers[:3]
        records.append({"crop_name": crop, "prices": prices, "source_text": line})
    return records


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


def _normalize_html(text: str) -> list[dict[str, Any]]:
    parser = _TableParser()
    parser.feed(text)
    if not parser.rows:
        return _normalize_document(re.sub(r"<[^>]+>", "\n", text))
    return _normalize_document("\n".join(f"| {' | '.join(row)} |" for row in parser.rows))


def _extract_result_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _extract_result_text(item)]
    if isinstance(value, dict):
        preferred = [value[key] for key in ("content", "text", "value", "blocks") if key in value]
        if preferred:
            return [text for item in preferred for text in _extract_result_text(item)]
    if hasattr(value, "model_dump"):
        return _extract_result_text(value.model_dump())
    return []


def _normalize_extracted_payload(value: Any) -> list[dict[str, Any]]:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        candidate = value.get("crops") or value.get("items") or value.get("rows")
        if candidate is not None:
            return _normalize_extracted_payload(candidate)
        crop_name = value.get("crop_name") or value.get("crop") or value.get("commodity") or value.get("name")
        if isinstance(crop_name, str):
            raw_prices = value.get("prices") if isinstance(value.get("prices"), dict) else value
            prices = {
                key: _number(raw_prices.get(key))
                for key in ("min", "max", "modal")
            }
            if not any(price is not None for price in prices.values()):
                numbers = [_number(raw_prices.get(key)) for key in ("price", "value", "rate")]
                numbers = [number for number in numbers if number is not None]
                if numbers:
                    prices["modal"] = numbers[0]
            if any(price is not None for price in prices.values()):
                return [{"crop_name": crop_name.strip(), "prices": prices, "source_text": None}]
        return [record for item in value.values() for record in _normalize_extracted_payload(item)]
    if isinstance(value, list):
        return [record for item in value for record in _normalize_extracted_payload(item)]
    if isinstance(value, str):
        try:
            return _normalize_extracted_payload(json.loads(value))
        except json.JSONDecodeError:
            return _normalize_document(value)
    return []


def _vision_sync(
    image: bytes,
    filename: str,
    content_type: str,
    language_code: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    client = _client(settings)
    try:
        schema = {
            "type": "object",
            "properties": {
                "crops": {
                    "type": "array",
                    "description": "Every crop row visible on the mandi price board.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "crop_name": {"type": "string", "description": "Crop name exactly as shown."},
                            "min": {"type": "number", "description": "Minimum price, if shown."},
                            "max": {"type": "number", "description": "Maximum price, if shown."},
                            "modal": {"type": "number", "description": "Modal price, if shown."},
                        },
                    },
                }
            },
        }
        job = client.doc_ai.extract(
            file=[(filename, image, content_type)],
            schema=json.dumps(schema),
            output_format="json",
        )
    except (ApiError, OSError, TimeoutError, TypeError, ValueError) as exc:
        raise _vision_stage_error("submission", exc) from exc
    deadline = time.monotonic() + settings.request_timeout_seconds
    terminal_states = {"completed", "partially_completed", "failed", "rejected"}
    while True:
        try:
            status = client.doc_ai.get_status(job_id=job.job_id)
        except (ApiError, OSError, TimeoutError, TypeError, ValueError) as exc:
            raise _vision_stage_error("status check", exc) from exc
        state = str(_field(status, "status", "")).lower()
        if state in terminal_states:
            break
        if time.monotonic() >= deadline:
            raise TimeoutError("Vision service timed out")
        time.sleep(2)
    if state not in {"completed", "partially_completed"}:
        raise SarvamError(f"Vision service returned status {state}")
    try:
        result = client.doc_ai.get_results(job.job_id)
    except (ApiError, OSError, TimeoutError, TypeError, ValueError) as exc:
        raise _vision_stage_error("result retrieval", exc) from exc
    structured = _field(result, "result")
    if structured is not None:
        return _normalize_extracted_payload(structured)
    documents = _field(result, "documents", [])
    contents = [
        _extract_result_text(page)
        for document in documents
        for page in (_field(document, "pages", []) or [])
    ]
    return _normalize_document("\n".join(text for page in contents for text in page))


async def call_vision(
    image: bytes,
    filename: str,
    content_type: str,
    language_code: str,
    settings: Settings,
) -> list[dict[str, Any]]:
    try:
        return await asyncio.to_thread(_vision_sync, image, filename, content_type, language_code, settings)
    except ApiError as exc:
        raise _provider_error("Vision service rejected the request", exc) from exc
    except (OSError, TimeoutError, ValueError) as exc:
        raise SarvamError("Vision service request failed") from exc


def _speech_sync(audio: bytes, filename: str, content_type: str, crop_name: str, language_code: str, settings: Settings) -> dict[str, Any]:
    response = _client(settings).speech_to_text.transcribe(
        file=(filename, audio, content_type),
        model=settings.sarvam_speech_model,
        language_code=language_code,
        keyterms=[crop_name] if crop_name else None,
    )
    transcript = _field(response, "transcript", "")
    price, prices = extract_price(transcript if isinstance(transcript, str) else "")
    return {
        "transcript": transcript if isinstance(transcript, str) else "",
        "extracted_price": price,
        "ambiguous_prices": prices if len(prices) > 1 else [],
    }


async def transcribe(
    audio: bytes,
    filename: str,
    content_type: str,
    crop_name: str,
    language_code: str,
    settings: Settings,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(_speech_sync, audio, filename, content_type, crop_name, language_code, settings)
    except ApiError as exc:
        raise _provider_error("Speech service rejected the request", exc) from exc
    except (OSError, TimeoutError, ValueError) as exc:
        raise SarvamError("Speech service request failed") from exc


def _tts_sync(text: str, language_code: str, settings: Settings) -> tuple[bytes, str]:
    response = _client(settings).text_to_speech.convert(
        text=text,
        language_code=language_code,
        speaker="shubh",
        model=settings.sarvam_tts_model,
    )
    audios = _field(response, "audios", [])
    if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
        raise SarvamError("Text-to-speech returned no audio")
    return base64.b64decode(audios[0]), "audio/wav"


async def synthesize(text: str, language_code: str, settings: Settings) -> tuple[bytes, str]:
    try:
        return await asyncio.to_thread(_tts_sync, text, language_code, settings)
    except ApiError as exc:
        raise _provider_error("Text-to-speech service rejected the request", exc) from exc
    except (OSError, TimeoutError, ValueError) as exc:
        raise SarvamError("Text-to-speech service request failed") from exc
