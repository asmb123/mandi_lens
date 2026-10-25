import pytest

from app.services.comparison import compare_prices
from app.services.price_parser import extract_price, extract_prices
from app.services.sarvam import _extract_result_text, _normalize_document, _normalize_extracted_payload, _normalize_html


@pytest.mark.parametrize(
    ("board", "offered", "direction", "percentage"),
    [(2400, 1800, "below", 25), (1800, 2400, "above", -33.33), (1800, 1800, "equal", 0)],
)
def test_compare_prices(board: int, offered: int, direction: str, percentage: float) -> None:
    result = compare_prices(board, offered)
    assert result["direction"] == direction
    assert result["difference_percentage"] == percentage


def test_zero_board_price_has_no_percentage() -> None:
    assert compare_prices(0, 100)["difference_percentage"] is None


def test_negative_prices_are_rejected() -> None:
    with pytest.raises(ValueError):
        compare_prices(-1, 1)


def test_price_parser_handles_currency_formats() -> None:
    assert extract_prices("प्याज़ का भाव ₹1,800 रुपये") == [1800]
    assert extract_price("भाव 1800 रुपये") == (1800, [1800])


def test_price_parser_flags_ambiguous_numbers() -> None:
    assert extract_price("1800 या 1900 रुपये") == (None, [1800, 1900])


def test_vision_markdown_preserves_price_columns() -> None:
    records = _normalize_document(
        "| Crop | Min | Max | Modal |\n|---|---:|---:|---:|\n| टमाटर | ₹1,800 | ₹2,600 | ₹2,400 |"
    )
    assert records == [{
        "crop_name": "टमाटर",
        "prices": {"min": 1800, "max": 2600, "modal": 2400},
        "source_text": "| टमाटर | ₹1,800 | ₹2,600 | ₹2,400 |",
    }]


def test_vision_html_preserves_price_columns() -> None:
    records = _normalize_html(
        "<table><tr><th>Crop</th><th>Min</th><th>Max</th><th>Modal</th></tr>"
        "<tr><td>टमाटर</td><td>₹1,800</td><td>₹2,600</td><td>₹2,400</td></tr></table>"
    )
    assert records[0]["prices"] == {"min": 1800, "max": 2600, "modal": 2400}


def test_vision_json_result_text_is_extracted() -> None:
    value = {"blocks": [{"text": "| टमाटर | ₹2,400 |"}]}
    assert _extract_result_text(value) == ["| टमाटर | ₹2,400 |"]


def test_vision_json_model_result_text_is_extracted() -> None:
    class Page:
        def model_dump(self) -> dict[str, list[dict[str, str]]]:
            return {"blocks": [{"text": "| प्याज़ | ₹1,800 |"}]}

    assert _extract_result_text(Page()) == ["| प्याज़ | ₹1,800 |"]


def test_structured_vision_extraction_returns_crop_prices() -> None:
    records = _normalize_extracted_payload({
        "crops": [{"crop_name": "टमाटर", "min": 1800, "max": 2600, "modal": 2400}]
    })
    assert records == [{
        "crop_name": "टमाटर",
        "prices": {"min": 1800, "max": 2600, "modal": 2400},
        "source_text": None,
    }]
