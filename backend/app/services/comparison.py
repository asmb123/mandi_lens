from typing import Literal


def compare_prices(board_price: int, offered_price: int) -> dict[str, int | float | None | Literal["below", "above", "equal"]]:
    if board_price < 0 or offered_price < 0:
        raise ValueError("Prices cannot be negative")
    difference = board_price - offered_price
    direction: Literal["below", "above", "equal"] = (
        "below" if difference > 0 else "above" if difference < 0 else "equal"
    )
    percentage = round((difference / board_price) * 100, 2) if board_price > 0 else None
    return {
        "board_price": board_price,
        "offered_price": offered_price,
        "difference": difference,
        "direction": direction,
        "difference_percentage": percentage,
    }
