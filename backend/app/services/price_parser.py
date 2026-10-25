import re


_DIGIT_PRICE = re.compile(r"(?<!\d)(?:₹\s*)?(\d[\d,]*)(?:\s*(?:रुपये|रुपया|रूपये|रुपए|rs\.?|inr))?(?!\d)", re.IGNORECASE)
_HINDI_UNITS = {
    "शून्य": 0,
    "एक": 1,
    "दो": 2,
    "तीन": 3,
    "चार": 4,
    "पाँच": 5,
    "छह": 6,
    "सात": 7,
    "आठ": 8,
    "नौ": 9,
    "दस": 10,
    "ग्यारह": 11,
    "बारह": 12,
    "तेरह": 13,
    "चौदह": 14,
    "पंद्रह": 15,
    "सोलह": 16,
    "सत्रह": 17,
    "अठारह": 18,
    "उन्नीस": 19,
    "बीस": 20,
    "तीस": 30,
    "चालीस": 40,
    "पचास": 50,
    "साठ": 60,
    "सत्तर": 70,
    "अस्सी": 80,
    "नब्बे": 90,
}


def extract_prices(text: str) -> list[int]:
    """Extract only currency-shaped numbers or explicitly supported number words."""
    values = [int(match.replace(",", "")) for match in _DIGIT_PRICE.findall(text)]
    words = [word for word in re.split(r"\s+", text) if word in _HINDI_UNITS]
    if words and not values:
        values.append(sum(_HINDI_UNITS[word] for word in words))
    return list(dict.fromkeys(value for value in values if value >= 0))


def extract_price(text: str) -> tuple[int | None, list[int]]:
    prices = extract_prices(text)
    return (prices[0] if len(prices) == 1 else None, prices)
