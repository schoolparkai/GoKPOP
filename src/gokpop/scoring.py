"""Pure scoring functions and explicit approval gates for GOKPOP 2.0.

The functions do not read or write a ledger, infer human classifications, or
turn conditional formulae into approved public scores. Fractions preserve the
strict finite-input upper bounds before display rounding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Mapping


ENGINE_VERSION = "gokpop2-phase2a-1"
DESIGN_ID = "gokpop2-phase1-final-20261017"
MAX_COUNT = 2**64 - 1
MAX_NUMERIC_TEXT_LENGTH = 1024
MAX_RATIONAL_BITS = 4096
METRIC_NAMES = ("B1", "E1", "E2", "E3", "I1", "I2")
MAX_SCORES = MappingProxyType(
    {"B1": 20, "E1": 8, "E2": 10, "E3": 27, "I1": 10, "I2": 25}
)
MODES = frozenset({"official", "conditional_design", "simulation"})
SUPPORTED_FORMULA_VERSION = "gokpop2-engine-v1"
FORMULA_VERSION = SUPPORTED_FORMULA_VERSION
# Implementing a version is not approval to use its conditional components.
# A public release must separately carry user approval for this exact config.
FORMULA_CONFIG = {
    "design_id": DESIGN_ID,
    "formula_version": SUPPORTED_FORMULA_VERSION,
    "maximum_scores": dict(MAX_SCORES),
    "B1": {"fixed": 20, "distinct_phrases": 15, "inventive_phrases": 3},
    "E1": {
        "type": "fixed_evidence_performance",
        "chart_size": 200,
        "entry_weight": 3,
        "best_observed_rank_weight": 2,
        "different_week_repeat_weight": 1,
        "following_release_year_download_weight": 2,
        "rank_normalization": "(201-r)/200",
        "scope": "explicit_fixed_evidence_set",
    },
    "E2": {"weights": [6, 4], "K": [10000000, 50000], "units": ["views", "likes"]},
    "E3": {
        "weights": [12, 11, 4], "K": [100, 10, 40],
        "units": ["allocated_T_mass", "allocated_A_mass", "fixed_cohort_response_mass"],
        "shared_TA_allocation": ["0.5", "0.5"],
        "cohort": "fixed_UTC_quarter_and_top_or_reply; min30; year_fallback",
        "social_response": "zero_likes=0; positive=max(0,2*midrank_percentile-1); expression_group_max",
    },
    "I1": {"weights": [6, 4], "K": [125000, 2500], "units": ["views", "likes"]},
    "I2": {"weight": 25, "K": 2, "unit": "human_validated_independent_meaning_cases"},
    "normalization": "h(x;K)=x/(x+K)",
    "count_range": [0, MAX_COUNT],
    "numeric_representation_limits": {
        "decimal_text_characters": MAX_NUMERIC_TEXT_LENGTH,
        "decimal_absolute_scale_exponent": MAX_NUMERIC_TEXT_LENGTH,
        "rational_numerator_or_denominator_bits": MAX_RATIONAL_BITS,
    },
    "calculation_precision": "exact_rational",
}
CONFIG_SHA256 = hashlib.sha256(
    json.dumps(FORMULA_CONFIG, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
).hexdigest()


class InputValidationError(ValueError):
    """A supplied value has the wrong unit, range, or numeric representation."""


def validate_count(value: object, name: str = "count") -> int:
    """Accept a nonnegative uint64 integer or an ASCII integer text input.

    Booleans, floats (including 1.0), fractional values, missing values and
    scientific notation are deliberately rejected. Browser inputs can pass
    integer text without losing precision through a JavaScript number.
    """
    if isinstance(value, bool):
        raise InputValidationError(f"{name}: 참/거짓 값은 개수가 아닙니다.")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        text = value.strip().lstrip("0") or "0"
        if len(text) > 20:
            raise InputValidationError(f"{name}: 지원 범위는 0~{MAX_COUNT}입니다.")
        result = int(text)
    else:
        raise InputValidationError(f"{name}: 결측·소수 없이 0 이상의 정수를 입력하세요.")
    if not 0 <= result <= MAX_COUNT:
        raise InputValidationError(f"{name}: 지원 범위는 0~{MAX_COUNT}입니다.")
    return result


def _nonnegative_fraction(value: object, name: str) -> Fraction:
    """Convert finite nonnegative mass/score values without binary-float noise.

    Representation limits prevent compact hostile exponents from allocating
    enormous integers. They exceed observed-corpus precision and do not change
    scoring coefficients or saturation constants.
    """
    if isinstance(value, bool):
        raise InputValidationError(f"{name}: 참/거짓 값은 수치가 아닙니다.")
    if isinstance(value, Fraction):
        if value.numerator.bit_length() > MAX_RATIONAL_BITS or value.denominator.bit_length() > MAX_RATIONAL_BITS:
            raise InputValidationError(f"{name}: 수치 표현이 지원 정밀도를 초과합니다.")
        result = value
    elif isinstance(value, int):
        if value.bit_length() > MAX_RATIONAL_BITS:
            raise InputValidationError(f"{name}: 수치 표현이 지원 정밀도를 초과합니다.")
        result = Fraction(value)
    elif isinstance(value, Decimal):
        if not value.is_finite():
            raise InputValidationError(f"{name}: 유한한 수치가 필요합니다.")
        if len(value.as_tuple().digits) > MAX_NUMERIC_TEXT_LENGTH or abs(value.as_tuple().exponent) > MAX_NUMERIC_TEXT_LENGTH:
            raise InputValidationError(f"{name}: 수치 표현이 지원 정밀도를 초과합니다.")
        result = Fraction(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise InputValidationError(f"{name}: 유한한 수치가 필요합니다.")
        result = Fraction(Decimal(str(value)))
    elif isinstance(value, str):
        if len(value) > MAX_NUMERIC_TEXT_LENGTH:
            raise InputValidationError(f"{name}: 수치 표현이 너무 깁니다.")
        try:
            decimal_value = Decimal(value.strip())
            if not decimal_value.is_finite():
                raise InvalidOperation
            if abs(decimal_value.as_tuple().exponent) > MAX_NUMERIC_TEXT_LENGTH:
                raise InputValidationError(f"{name}: 수치 표현이 지원 정밀도를 초과합니다.")
            result = Fraction(decimal_value)
        except (InvalidOperation, ValueError, OverflowError) as exc:
            raise InputValidationError(f"{name}: 유한한 수치가 필요합니다.") from exc
    else:
        raise InputValidationError(f"{name}: 유한한 수치가 필요합니다.")
    if result < 0:
        raise InputValidationError(f"{name}: 음수는 허용하지 않습니다.")
    return result


def _saturating(x: Fraction | int, k: int, weight: int) -> Fraction:
    return weight * Fraction(x) / (Fraction(x) + k)


def calculate_i1(views: object, likes: object) -> Fraction:
    """Approved lecture engagement formula; exactly 8 at 500000 / 10000."""
    v, l = validate_count(views, "조회수"), validate_count(likes, "좋아요")
    return _saturating(v, 125000, 6) + _saturating(l, 2500, 4)


def calculate_e2(views: object, likes: object) -> Fraction:
    """Conditional original-track engagement formula; calculation is not approval."""
    v, l = validate_count(views, "조회수"), validate_count(likes, "좋아요")
    return _saturating(v, 10000000, 6) + _saturating(l, 50000, 4)


def calculate_e3(n_t: object, n_a: object, c_q: object) -> Fraction:
    """Conditional normalized masses, after separate human validation/deduplication.

    n_t/n_a are allocated reception mass (shared T/A contributes 0.5 each).
    c_q is fixed-cohort normalized social-response mass, not raw likes. This
    aggregate function never classifies comments or accepts provisional cases.
    """
    t = _nonnegative_fraction(n_t, "nT")
    a = _nonnegative_fraction(n_a, "nA")
    c = _nonnegative_fraction(c_q, "cQ")
    return _saturating(t, 100, 12) + _saturating(a, 10, 11) + _saturating(c, 40, 4)


def calculate_i2(cases: object) -> Fraction:
    """Conditional score for independent approved meaning cases, not commenters."""
    return _saturating(validate_count(cases, "독립 의미 사례 U"), 2, 25)


def _rank(value: object, name: str) -> int:
    result = validate_count(value, name)
    if not 1 <= result <= 200:
        raise InputValidationError(f"{name}: 1~200위만 허용합니다.")
    return result


def calculate_e1(
    weekly_ranks: Mapping[str, object],
    annual_rank: object | None,
    evidence_complete: bool = True,
) -> Fraction:
    """Conditional fixed-evidence composite, never a reconstructed 52-week area.

    Keys must be unique ISO week IDs (YYYY-Www). An empty mapping explicitly
    represents verified absence in the declared evidence scope. Unknown scope
    or an unknown annual result cannot be silently filled with zero. The caller
    records that scope and separately approves its use in an official index.
    """
    if evidence_complete is not True:
        raise InputValidationError("E1: 고정 근거집합의 검증이 완료되지 않았습니다.")
    if not isinstance(weekly_ranks, Mapping):
        raise InputValidationError("E1: 주차별 순위 매핑이 필요합니다.")
    ranks: list[int] = []
    for week, value in weekly_ranks.items():
        if not isinstance(week, str) or not re.fullmatch(r"[0-9]{4}-W[0-9]{2}", week):
            raise InputValidationError("E1: 주차는 YYYY-Www 형식이어야 합니다.")
        try:
            date.fromisocalendar(int(week[:4]), int(week[-2:]), 1)
        except ValueError as exc:
            raise InputValidationError("E1: 유효하지 않은 ISO 주차입니다.") from exc
        ranks.append(_rank(value, "주간 디지털 순위"))
    if annual_rank is None:
        raise InputValidationError("E1: 다음 해 연간 다운로드 결과가 결측입니다.")
    annual = _rank(annual_rank, "다음 해 연간 다운로드 순위")
    score = Fraction(201 - annual, 100)
    if ranks:
        score += 3 + Fraction(201 - min(ranks), 100)
    if len(ranks) >= 2:
        score += 1
    return score


@dataclass(frozen=True)
class MetricInput:
    """Numeric value plus independent formula, validation and human-approval states."""

    value: Fraction | None = None
    formula_status: str = "conditional"
    validation_status: str = "pending"
    approval_status: str = "pending"
    reason: str = ""

    def __post_init__(self) -> None:
        if self.value is not None:
            object.__setattr__(self, "value", _nonnegative_fraction(self.value, "점수"))


@dataclass(frozen=True)
class ScoreResult:
    mode: str
    components: Mapping[str, Fraction | None]
    total: Fraction | None
    reasons: tuple[str, ...]


def _official_reasons(name: str, metric: MetricInput) -> list[str]:
    reasons: list[str] = []
    if metric.value is None:
        reasons.append(f"{name}: 검증된 입력이 없습니다.")
    if metric.formula_status != "approved":
        reasons.append(f"{name}: 계산식의 최종 승인이 필요합니다.")
    if metric.validation_status != "validated":
        reasons.append(f"{name}: 입력·판정 검증이 완료되지 않았습니다.")
    if metric.approval_status != "user_approved":
        reasons.append(f"{name}: 사용자 승인이 완료되지 않았습니다.")
    if reasons and metric.reason:
        reasons.append(f"{name}: {metric.reason}")
    return reasons


def compute_index(
    metrics: Mapping[str, MetricInput], mode: str = "official"
) -> ScoreResult:
    """Compute a total only when the requested mode's explicit gates are met.

    B1 is the approved immutable 20. Missing metrics remain None. In official
    mode each other metric needs approved/validated/user_approved states. In
    conditional_design mode supplied provisional values are retained with their
    reasons. Simulation accepts an experience-only I1 and requires all other
    components to satisfy the official gates. Publication is an additional data
    loader concern; an approved calculated total is not a published observation.
    """
    if mode not in MODES:
        raise InputValidationError(f"지원하지 않는 계산 모드: {mode}")
    if not isinstance(metrics, Mapping):
        raise InputValidationError("지표별 입력 매핑이 필요합니다.")
    unknown = set(metrics) - set(METRIC_NAMES)
    if unknown:
        raise InputValidationError("알 수 없는 지표가 있습니다.")
    if any(not isinstance(value, MetricInput) for value in metrics.values()):
        raise InputValidationError("각 지표에는 MetricInput이 필요합니다.")
    supplied_b1 = metrics.get("B1")
    if supplied_b1 and supplied_b1.value is not None and supplied_b1.value != 20:
        raise InputValidationError("B1은 승인 정본에 따라 20점으로 고정됩니다.")
    components: dict[str, Fraction | None] = {"B1": Fraction(20)}
    reasons: list[str] = []
    for name in METRIC_NAMES[1:]:
        metric = metrics.get(name, MetricInput())
        if metric.value is not None:
            limit = MAX_SCORES[name]
            if metric.value > limit or (name in {"E2", "E3", "I1", "I2"} and metric.value == limit):
                raise InputValidationError(f"{name}: 유한 입력의 점수 상한을 벗어났습니다.")
        problems = _official_reasons(name, metric)
        if mode == "conditional_design":
            components[name] = metric.value
            reasons.extend(problems)
        elif mode == "simulation" and name == "I1" and (
            metric.value is not None
            and metric.formula_status == "approved"
            and metric.validation_status == "simulation"
            and metric.approval_status == "experience_only"
        ):
            components[name] = metric.value
        else:
            components[name] = metric.value if not problems else None
            reasons.extend(problems)
    total = (
        sum((value for value in components.values() if value is not None), Fraction())
        if all(value is not None for value in components.values())
        else None
    )
    return ScoreResult(mode, MappingProxyType(components), total, tuple(reasons))


def simulate_i1(
    metrics: Mapping[str, MetricInput], views: object, likes: object
) -> ScoreResult:
    """Return a new in-memory experience result, without mutating the base inputs."""
    simulated = dict(metrics)
    simulated["I1"] = MetricInput(
        calculate_i1(views, likes), "approved", "simulation", "experience_only"
    )
    return compute_index(simulated, mode="simulation")


def format_score(value: Fraction | None, maximum: int | None = None, digits: int = 2) -> str:
    """Display values without rounding an unattainable finite upper bound to full marks."""
    if value is None:
        return "확인 중"
    if digits < 0 or digits > 6:
        raise InputValidationError("표시 소수 자릿수는 0~6이어야 합니다.")
    text = f"{float(value):.{digits}f}"
    if maximum is not None and value < maximum and text == f"{maximum:.{digits}f}":
        return f"<{maximum:.{digits}f}"
    return text
