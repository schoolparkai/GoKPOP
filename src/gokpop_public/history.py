"""Dated lecture observations, separate from the frozen official score edition.

Only the supplied lecture counts change. The existing exact scoring engine is
reused; no original-track observations, approvals or intermediate days are
created. Dates are calendar dates confirmed by the researcher, not timestamps.
"""
from datetime import date
from fractions import Fraction
import json
from pathlib import Path

from gokpop.presentation import format_score
from gokpop.scoring import FORMULA_VERSION, validate_count
from .content import load_content, simulate


RELATIVE = 'data/public/lecture_history.json'
SCHEMA = 'gokpop-lecture-observations-v1'
METRICS = {
    '조회수': ('views', '조회수 (회)', ',.0f', None),
    '좋아요': ('likes', '좋아요 (개)', ',.0f', None),
    '강의 영상 점수': ('I1', '강의 영상 점수 (10점 만점)', '.3f', 10),
    '종합지수 비교': ('J_comparison', '종합지수 비교 (100점 만점)', '.2f', 100),
}


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError('관측 자료의 항목을 확인해 주세요.')


def _calendar_day(value):
    if not isinstance(value, str):
        raise ValueError('관측일은 YYYY-MM-DD 형식이어야 합니다.')
    day = date.fromisoformat(value)
    if day.isoformat() != value:
        raise ValueError('관측일은 YYYY-MM-DD 형식이어야 합니다.')
    return day


def prepare_history(payload, content):
    """Validate raw records and return exact, newly allocated derived rows."""
    _keys(payload, {'schema', 'video_url', 'formula_version', 'baseline_date', 'source', 'observations'})
    baseline_day = _calendar_day(content['baseline_date'])
    lecture = content['observations']['I1']
    if (payload['schema'] != SCHEMA
            or payload['video_url'] != lecture['url']
            or payload['formula_version'] != FORMULA_VERSION
            or payload['baseline_date'] != baseline_day.isoformat()
            or payload['source'] != 'researcher_confirmed_screenshots'):
        raise ValueError('관측 대상이나 계산 기준이 기존 기록과 다릅니다.')
    if not isinstance(payload['observations'], list):
        raise ValueError('날짜별 관측 목록이 필요합니다.')
    records = [{'date': baseline_day.isoformat(), 'views': lecture['views'], 'likes': lecture['likes']}]
    seen = {baseline_day}
    for item in payload['observations']:
        _keys(item, {'date', 'views', 'likes'})
        observed_day = _calendar_day(item['date'])
        if observed_day <= baseline_day or observed_day in seen:
            raise ValueError('첫 기준일 이후의 중복 없는 관측일이 필요합니다.')
        seen.add(observed_day)
        # Persisted data uses real JSON integers, not user-input numeric strings.
        if type(item['views']) is not int or type(item['likes']) is not int:
            raise ValueError('조회수와 좋아요는 정수여야 합니다.')
        records.append({'date': item['date'],
                        'views': validate_count(item['views'], '조회수'),
                        'likes': validate_count(item['likes'], '좋아요')})
    records.sort(key=lambda row: row['date'])
    baseline_score = Fraction(content['scores_exact']['I1'])
    for row in records:
        result = simulate(content, row['views'], row['likes'])
        row['I1_exact'] = result['I1']
        row['J_comparison_exact'] = result['J']
        row['I1_change'] = result['I1'] - baseline_score
        # A comparison calculation must not become an approved J observation.
        row['J_official_exact'] = Fraction(content['J_exact']) if row['date'] == content['baseline_date'] else None
        row['days_from_baseline'] = (_calendar_day(row['date']) - baseline_day).days
    if records[0]['I1_exact'] != baseline_score:
        raise ValueError('첫 관측 점수가 기존 계산식과 일치하지 않습니다.')
    return records


def load_history(root, content=None):
    if content is None:
        content = load_content(root)
    payload = json.loads((Path(root) / RELATIVE).read_text(encoding='utf-8'))
    return prepare_history(payload, content)


def chart_spec(records, metric='조회수', zoom=True):
    """Temporal spacing is proportional to actual dates; all observed points remain."""
    if metric not in METRICS:
        raise ValueError('표시할 지표를 확인해 주세요.')
    field, title, number_format, maximum = METRICS[metric]
    values = [
        {'date': row['date'], 'observation_date': row['date'], 'views': row['views'], 'likes': row['likes'],
         'I1': float(row['I1_exact']), 'J_comparison': float(row['J_comparison_exact'])}
        for row in records
    ]
    scale = {'zero': False} if zoom else ({'domain': [0, maximum]} if maximum else {'zero': True})
    mark = {'type': 'line', 'point': {'filled': True, 'size': 75}, 'color': '#1c6355', 'interpolate': 'linear'}
    if metric == '종합지수 비교':
        mark['strokeDash'] = [6, 4]
    tooltip = [
        # Vega parses the temporal x field into milliseconds. Keep a separate
        # original calendar label for timezone-independent, readable details.
        {'field': 'observation_date', 'type': 'nominal', 'title': '관측일'},
        {'field': 'views', 'type': 'quantitative', 'title': '조회수', 'format': ',.0f'},
        {'field': 'likes', 'type': 'quantitative', 'title': '좋아요', 'format': ',.0f'},
    ]
    if field not in {'views', 'likes'}:
        tooltip.append({'field': field, 'type': 'quantitative', 'title': title, 'format': number_format})
    return {
        '$schema': 'https://vega.github.io/schema/vega-lite/v6.json',
        'data': {'values': values}, 'height': 270, 'mark': mark,
        'encoding': {
            'x': {'field': 'date', 'type': 'temporal', 'title': '실제 관측일',
                  'scale': {'type': 'utc'}, 'axis': {'format': '%m/%d', 'labelAngle': 0, 'tickCount': 4}},
            'y': {'field': field, 'type': 'quantitative', 'title': title, 'scale': scale,
                  'axis': {'format': number_format}},
            'tooltip': tooltip,
        },
        'config': {'background': 'transparent', 'view': {'stroke': None},
                   'axis': {'labelColor': '#56675f', 'titleColor': '#56675f', 'gridColor': '#e6e9e3'}},
    }


def render_history(root, content):
    import streamlit as st

    try:
        records = load_history(root, content)
    except (OSError, ValueError, TypeError, KeyError):
        st.info('날짜별 관측 기록을 불러오지 못했습니다. 다른 기능은 계속 이용할 수 있습니다.')
        return
    first, latest = records[0], records[-1]
    st.header('함께 쌓아 온 반응', anchor=False)
    st.caption(f'{first["date"].replace("-", ".")}–{latest["date"].replace("-", ".")} · 실제 관측 {len(records)}회')
    st.markdown(
        f'최근 강의 영상 반응은 **조회수 {latest["views"]:,}회 · 좋아요 {latest["likes"]:,}개**입니다. '
        f'첫 기록보다 조회수 **{latest["views"] - first["views"]:+,}회**, '
        f'좋아요 **{latest["likes"] - first["likes"]:+,}개** 달라졌습니다.'
    )
    metric = st.radio('그래프로 볼 기록', tuple(METRICS), horizontal=True, key='lecture_history_metric')
    zoom = st.checkbox('변화 폭 확대 보기', value=True, key='lecture_history_zoom')
    if metric == '종합지수 비교':
        st.markdown('**강의 영상 반응을 반영한 종합지수 비교**')
        st.caption('원곡 영상 등 다른 지표는 2026년 10월 18일 값으로 고정한 비교 계산입니다. 각 날짜의 모든 지표를 새로 측정한 공식 종합지수와는 다릅니다.')
    elif metric == '강의 영상 점수':
        st.caption(f'최근 강의 영상 점수: {format_score(latest["I1_exact"], 10, 3)} / 10점 · 첫 기록 대비 {float(latest["I1_change"]):+.3f}점')
    st.vega_lite_chart(chart_spec(records, metric, zoom), width='stretch')
    if zoom:
        st.caption('세로축을 관측 범위에 맞춰 확대했습니다. 점은 실제 기록이며, 관측일 사이의 수치는 채우지 않았습니다.')
    else:
        st.caption('점은 실제 기록이며, 관측일 사이의 수치는 채우지 않았습니다.')
    with st.expander('관측점 자세히 보기'):
        selected_date = st.selectbox('확인할 관측일', [row['date'] for row in records],
                                    index=len(records) - 1, key='lecture_history_detail_date')
        selected = next(row for row in records if row['date'] == selected_date)
        st.markdown(f'**{selected_date}** · 조회수 **{selected["views"]:,}회** · 좋아요 **{selected["likes"]:,}개**')
        st.markdown(f'강의 영상 점수 **{format_score(selected["I1_exact"], 10, 3)} / 10점** · '
                    f'종합지수 비교 **{format_score(selected["J_comparison_exact"], 100, 2)} / 100점**')
        st.caption('종합지수 비교는 원곡 영상 등 다른 지표를 2026년 10월 18일 값으로 고정한 계산입니다. 관측 시각은 새로 만들지 않았습니다.')
    with st.expander('날짜별 수치 보기'):
        table = [
            {'관측일': row['date'], '조회수': row['views'], '좋아요': row['likes'],
             '강의 영상 점수': format_score(row['I1_exact'], 10, 3),
             '종합지수 비교': format_score(row['J_comparison_exact'], 100, 2)}
            for row in records
        ]
        st.dataframe(table, hide_index=True, width='stretch')
        st.caption('종합지수 비교는 원곡 영상 등 다른 지표를 첫 관측값으로 고정한 계산입니다. 제공된 화면에서 수치를 읽고 연구자가 확인한 날짜에 연결했습니다.')
