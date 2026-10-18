"""Strict minimal staging data contract and memory-only audience calculations."""
from copy import deepcopy
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from gokpop.scoring import MAX_SCORES, calculate_e2, calculate_i1

SCHEMA = 'gokpop-release-data-v1'
RELATIVE = 'data/public/site_data.json'
EXPECTED_SHA256 = 'daf9b5e365a8efb8edf0a79ca156d3bdb8b8e13969dfaf9e44a9b7dbf1978d91'
NOTE_SHA256 = '1972f07357d8b1b0d5663976ba0a29e26a31f786ffab7c17f2efc048a485d222'
J_EXACT = "108635854215402719324112991267489459324348957507410163/1564533622402778194397265309011729426330992561574100"


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("기준 자료의 허용 항목이 다릅니다.")


def validate_content(value):
    """Reject unexpected/private fields and invented history; no score approval here."""
    _keys(value, {"schema", "baseline_date", "scores_exact", "J_exact", "observations", "charts", "counts", "records", "audience_note"})
    if value['schema'] != SCHEMA or value['baseline_date'] != '2026-10-18' or value['J_exact'] != J_EXACT:
        raise ValueError('승인된 기준 자료와 다릅니다.')
    scores = value["scores_exact"]
    _keys(scores, MAX_SCORES)
    if sum(map(Fraction, scores.values())) != Fraction(J_EXACT):
        raise ValueError("정확 합계가 다릅니다.")
    if any(not 0 <= Fraction(scores[k]) <= cap for k, cap in MAX_SCORES.items()):
        raise ValueError("배점 범위를 벗어났습니다.")
    if scores["B1"] != "20" or scores["E1"] != "643/100" or scores["I2"] != "50/3":
        raise ValueError("정적 승인값이 다릅니다.")
    _keys(value["observations"], {"E2", "I1"})
    for metric, vid, counts in (("E2", "m-DliVHOXjA", (14926224, 83113)), ("I1", "qRAMHmWnrLc", (55396, 1652))):
        row = value["observations"][metric]
        _keys(row, {"title", "channel", "url", "views", "likes", "observed_at_kst"})
        if row["url"] != "https://www.youtube.com/watch?v=" + vid or (row["views"], row["likes"]) != counts:
            raise ValueError("고정 관측·출처와 다릅니다.")
        stamp = datetime.fromisoformat(row["observed_at_kst"])
        if stamp.strftime("%Y-%m-%d %H:%M") != "2026-10-18 03:09" or stamp.utcoffset().total_seconds() != 32400:
            raise ValueError("고정 관측 시각과 다릅니다.")
        calc = calculate_e2 if metric == "E2" else calculate_i1
        if calc(row["views"], row["likes"]) != Fraction(scores[metric]):
            raise ValueError("관측 기반 계산값이 다릅니다.")
    if value["counts"] != {"E3_comments": 522, "E3_units": 498, "I2_cases": 4}:
        raise ValueError("승인 집계와 다릅니다.")
    expected = [("2022년 24주 디지털", 113), ("2022년 37주 디지털", 140), ("2022년 46주 디지털", 146), ("2023년 연간 다운로드", 46)]
    if len(value["charts"]) != 4:
        raise ValueError("차트 근거 범위가 다릅니다.")
    for row, (label, rank) in zip(value["charts"], expected):
        _keys(row, {"label", "rank", "url"})
        url = urlparse(row["url"])
        if row["label"] != label or row["rank"] != rank or url.scheme != "https" or url.hostname != "circlechart.kr":
            raise ValueError("차트 출처가 다릅니다.")
    # This frozen first edition contains exactly one actual point, no weekly fiction.
    expected_record = {"date": "2026-10-18", "kind": "baseline", "J_exact": J_EXACT,
                       "E2_exact": scores["E2"], "I1_exact": scores["I1"], "formula_version": "gokpop2-engine-v1"}
    if value["records"] != [expected_record]:
        raise ValueError("첫 기록 외에 승인되지 않은 관측점이 있습니다.")
    note = value['audience_note']
    _keys(note, {'title', 'summary', 'paragraphs'})
    text = '\n'.join([note['title'], *note['paragraphs']])
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != NOTE_SHA256:
        raise ValueError('승인된 감상 노트 문안과 다릅니다.')
    return deepcopy(value)


def load_content(root):
    path = Path(root) / RELATIVE
    raw = path.read_bytes()
    expected = EXPECTED_SHA256
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("기준 자료가 변경되었습니다.")
    return validate_content(json.loads(raw))


def simulate(value, views, likes):
    """Return an exact virtual result without modifying the supplied edition."""
    i1 = calculate_i1(views, likes)
    delta = i1 - Fraction(value["scores_exact"]["I1"])
    return {"I1": i1, "delta": delta, "J": Fraction(value["J_exact"]) + delta}


def history_chart(records):
    """Plot actual approved records only; do not connect formula revisions."""
    versions = list(dict.fromkeys(row["formula_version"] for row in records))
    rows = [{"date": row["date"], "J": float(Fraction(row["J_exact"])), "series": "계산 기준 " + str(versions.index(row["formula_version"]) + 1)} for row in records]
    mark = {"type": "point", "filled": True, "size": 130, "color": "#1c6355"} if len(rows) == 1 else {"type": "line", "point": True, "color": "#1c6355"}
    return {"data": {"values": rows}, "height": 180,
            "mark": mark,
            "encoding": {"x": {"field": "date", "type": "temporal", "title": None, "axis": {"format": "%m월 %d일", "tickCount": len(rows)}},
                         "y": {"field": "J", "type": "quantitative", "title": "종합지수", "scale": {"domain": [0, 100]}, "axis": {"values": [0, 25, 50, 75, 100]}},
                         "detail": {"field": "series"}, "tooltip": [{"field": "date", "type": "temporal", "title": "관측일", "format": "%Y-%m-%d"}, {"field": "J", "title": "점수", "format": ".2f"}]},
            "config": {"background": "transparent", "view": {"stroke": None}, "axis": {"labelColor": "#56675f", "titleColor": "#56675f", "gridColor": "#e6e9e3"}}}


def load_note(root):
    return load_content(root)['audience_note']
