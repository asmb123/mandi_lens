from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.config import get_settings
from app.schemas import ComparisonRequest, ComparisonResponse, CropPrice, OcrResponse, TranscriptionResponse
from app.services.comparison import compare_prices
from app.services.sarvam import SarvamError, call_vision, synthesize, transcribe

router = APIRouter(prefix="/api")
settings = get_settings()
_IMAGE_TYPES = {"image/jpeg", "image/png"}
_AUDIO_TYPES = {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ocr", response_model=OcrResponse)
async def ocr(file: UploadFile = File(...), language_code: str = Form("hi-IN")) -> OcrResponse:
    if file.content_type not in _IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported image type")
    contents = await file.read()
    if not contents or len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image is empty or too large")
    try:
        records = await call_vision(contents, file.filename or "board image", file.content_type, language_code, settings)
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return OcrResponse(success=bool(records), crops=[CropPrice(**record) for record in records], message=None if records else "No usable crop prices found")


@router.post("/speech/transcribe", response_model=TranscriptionResponse)
async def speech_transcribe(
    file: UploadFile = File(...),
    crop_name: str = Form(""),
    language_code: str = Form("unknown"),
) -> TranscriptionResponse:
    if file.content_type not in _AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio type")
    contents = await file.read()
    if not contents or len(contents) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Audio is empty or too large")
    try:
        result = await transcribe(
            contents,
            file.filename or "offer audio",
            file.content_type,
            crop_name,
            language_code,
            settings,
        )
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return TranscriptionResponse(success=bool(result["transcript"]), **result)


@router.post("/speech/synthesize")
async def speech_synthesize(text: str, language_code: str) -> Response:
    if not text.strip() or len(text) > 500:
        raise HTTPException(status_code=422, detail="Speech text is invalid")
    try:
        audio, content_type = await synthesize(text, language_code, settings)
    except SarvamError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(content=audio, media_type=content_type)


@router.post("/comparison", response_model=ComparisonResponse)
def comparison(request: ComparisonRequest) -> ComparisonResponse:
    return ComparisonResponse(**compare_prices(request.board_price, request.offered_price))
