from typing import Literal

from pydantic import BaseModel, Field, StrictInt


class CropPrice(BaseModel):
    crop_name: str = Field(min_length=1, max_length=200)
    prices: dict[Literal["min", "max", "modal"], int | None]
    source_text: str | None = None


class OcrResponse(BaseModel):
    success: bool
    crops: list[CropPrice] = Field(default_factory=list)
    message: str | None = None


class ComparisonRequest(BaseModel):
    board_price: StrictInt = Field(ge=0)
    offered_price: StrictInt = Field(ge=0)


class ComparisonResponse(ComparisonRequest):
    difference: int
    direction: Literal["below", "above", "equal"]
    difference_percentage: float | None


class TranscriptionResponse(BaseModel):
    success: bool
    transcript: str = ""
    extracted_price: int | None = None
    ambiguous_prices: list[int] = Field(default_factory=list)
    message: str | None = None
