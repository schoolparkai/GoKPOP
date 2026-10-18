"""Pure presentation helpers; no writes, collection, or approval transitions."""
from decimal import Decimal, localcontext
from fractions import Fraction


def format_score(value: Fraction | None, cap: int = 10, places: int = 2) -> str:
    if value is None:
        return "검증 중"
    with localcontext() as ctx:
        ctx.prec = 60
        number = Decimal(value.numerator) / Decimal(value.denominator)
        label = f"{number:.{places}f}"
    if value < cap and Decimal(label) >= cap:
        return f"<{cap:.{places}f}"
    return label


def format_delta(value: Fraction | None) -> str | None:
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        number = Decimal(value.numerator) / Decimal(value.denominator)
        return f"{number:+.3f}"


def weekly_chart_spec(items: list[dict], zoom: bool = False) -> dict:
    """Line groups are supplied by the validated loader, including missing-week breaks."""
    values = [
        {"date": row["observed_at_utc"], "score": float(row["total_score"]),
         "week": row["week_id"], "series": row["series_id"],
         "formula": row["formula_version"], "change": row.get("change_reason", "")}
        for row in items
    ]
    scale = {"domain": [0, 100]}
    if values and zoom:
        lo, hi = min(x["score"] for x in values), max(x["score"] for x in values)
        scale = {"domain": [max(0, lo - 2), min(100, hi + 2)], "zero": False}
    encoding = {
        "x": {"field": "date", "type": "temporal", "title": "실제 관측일 (한국시간)",
              "axis": {"format": "%m/%d", "labelAngle": 0}},
        "y": {"field": "score", "type": "quantitative", "title": "창작성 판단지수", "scale": scale},
        "detail": {"field": "series", "type": "nominal"},
        "tooltip": [
            {"field": "week", "title": "관측 주차"},
            {"field": "date", "type": "temporal", "title": "관측 시각", "format": "%Y-%m-%d %H:%M"},
            {"field": "score", "title": "지수", "format": ".2f"},
            {"field": "formula", "title": "공식 판본"},
            {"field": "change", "title": "변경 구분"},
        ],
    }
    # KST is an explicit UTC+9 offset in the displayed values, independent of browser timezone.
    from datetime import datetime, timedelta, timezone
    for row in values:
        dt = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
        row["date"] = dt.astimezone(timezone(timedelta(hours=9))).replace(tzinfo=None).isoformat()
    return {"$schema": "https://vega.github.io/schema/vega-lite/v6.json", "data": {"values": values},
            "layer": [{"mark": {"type": "line", "color": "#26685f", "strokeWidth": 2}, "encoding": encoding},
                      {"mark": {"type": "point", "filled": True, "size": 90, "color": "#26685f"}, "encoding": encoding}],
            "height": 260, "config": {"view": {"stroke": None}}}
