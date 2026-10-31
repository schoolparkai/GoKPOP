"""Public audience interface; calculations remain in session memory."""
from fractions import Fraction
from html import escape
import streamlit as st
from gokpop.presentation import format_score
from gokpop.scoring import MAX_SCORES
from .content import history_chart, load_content, simulate
from .content import load_note
from .history import load_history, render_history
from .media import support_banner, performance_video

LECTURE = 'https://www.youtube.com/watch?v=qRAMHmWnrLc'
MENUS = ('점수 보기', '직접 계산', '감상 노트')
LABELS = {'B1':'가사 창안성','E1':'음원 성과','E2':'원곡 영상 성과','E3':'대중의 가사 수용','I1':'강의 영상 성과','I2':'문학적 감상'}
DESCRIPTIONS = {
 'B1':'서로 다른 15구절 중 창안구 3개의 비율을 기본 20점으로 반영했습니다.',
 'E1':'확보한 주간 차트 3건과 이듬해 연간 차트 1건에 한정한 평가입니다.',
 'E2':'공식 제공 원곡 영상의 전 세계 조회수와 좋아요를 반영합니다.',
 'E3':'가사 인용·언급·활용 댓글 522건을 498개 감상 단위로 정리했습니다.',
 'I1':'연세대 강의 영상의 조회수와 좋아요를 반영합니다.',
 'I2':'기존 승인 범위의 독립 감상 의미 사례 4개를 반영합니다.'}
FORMULA_EXPLANATION = (
 '공개 강의에서는 노래 가사의 창안적 표현을 중심으로 창작성을 살펴보았습니다. 이후 음원과 원곡 영상의 성과 같은 외부 지표, 강의 영상의 반응 같은 내부 지표를 추가하여 평가 모형을 확장했습니다.',
 "특히 공식 공연 영상과 강의 영상에 남겨진 댓글을 분석하여, 사람들이 노랫말을 인용하고 활용하거나 그 의미와 감정을 받아들이는 **문학적 수용**을 수치화했습니다. 이러한 분석은 외부 지표인 '대중의 가사 수용'과 내부 지표인 '문학적 감상'에 각각 반영되었습니다.",
 '새로운 지수는 노래의 예술적 가치를 객관적으로 확정하려는 점수라기보다, **가사의 표현과 대중의 반응을 함께 살펴보는 탐색적·실험적 평가 모형**입니다.'
)

CSS = '''<style>
:root{--ink:#173c34;--muted:#56675e;--green:#276b58;--line:#dce3db;--paper:#f8f9f4}
.stApp{background:var(--paper);color:var(--ink)}
[data-testid="stHeader"]{background:transparent;height:0}
.block-container{max-width:850px;padding:1.8rem 2rem 2rem}
[data-testid="stVerticalBlock"]{gap:.85rem}
h1,h2,h3,p,label{color:var(--ink)}
h2{font-size:1.35rem!important;padding:.25rem 0!important;letter-spacing:-.04em}
button,a,input,summary{touch-action:manipulation}
[data-testid="stExpander"]{background:transparent;border-color:var(--line);border-radius:12px}
[data-testid="stExpander"] summary{min-height:48px;font-size:15px}
[data-testid="stButtonGroup"]{width:100%}
[data-testid="stButtonGroup"] button{flex:1;min-height:48px;font-size:16px;border-radius:10px!important;white-space:nowrap}
[data-testid="stButtonGroup"] button[aria-pressed="true"]{background:var(--ink);border-color:var(--ink);color:white}
[data-testid="stButtonGroup"] button[aria-pressed="true"] p{color:white}
[data-testid="stButton"] button,[data-testid="stLinkButton"] a{min-height:48px;border-radius:10px;font-size:15px}
[data-testid="stFormSubmitButton"] button{min-height:48px;border-radius:10px;font-size:16px;width:100%}
[data-testid="stFormSubmitButton"] button p{color:white}
[data-testid="stTextInput"] input{font-size:18px;min-height:48px;border-radius:10px}
.support-banner{display:grid;grid-template-columns:46px minmax(0,1fr);gap:12px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:2px}
.support-logo img{display:block;width:46px;height:auto}.support-banner p{font-size:12px;line-height:1.65;color:var(--muted);margin:0 0 3px}.support-channel{font-size:12px;line-height:1.65;color:var(--green);text-decoration:none;overflow-wrap:anywhere}
.masthead{display:flex;align-items:center;justify-content:space-between;margin:0 0 14px;gap:12px}
.brand{font-size:22px;font-weight:800;letter-spacing:-.035em}.brand span{font-weight:400}
.private-tag{font-size:12px;color:var(--muted);border:1px solid var(--line);border-radius:20px;padding:5px 9px}
.work-title{font-size:22px!important;font-weight:750;margin:0!important;padding:0!important;line-height:1.4;letter-spacing:-.04em}
.work-intro{font-size:14px;color:var(--muted);margin:7px 0 15px;line-height:1.6}
.hero{background:#eaf0e8;border:1px solid #dce5d8;border-radius:18px;padding:18px 24px}
.score-label{font-size:14px}.hero-score{font-size:76px;line-height:1.15;letter-spacing:-.07em;font-weight:760;color:#174e3c;font-variant-numeric:tabular-nums}
.hero-score small{font-size:20px;letter-spacing:-.03em;font-weight:450;margin-left:10px}
.baseline{font-size:13px;color:var(--muted);margin-top:7px}
.limit{font-size:14px;color:var(--muted);margin:11px 0 0;line-height:1.6}
.stat-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.stat{background:white;border:1px solid var(--line);border-radius:12px;padding:13px 8px;text-align:center}
.stat-label{font-size:13px;line-height:1.5;color:var(--muted);word-break:keep-all}
.stat-value{font-size:25px;font-weight:750;letter-spacing:-.04em;line-height:1.6}.stat-value small{font-size:13px;font-weight:400}
.record{border-left:3px solid var(--green);background:#edf1e8;border-radius:0 10px 10px 0;padding:12px 16px;font-size:14px;line-height:1.8}
.record strong{color:#174e3c}.record span{font-size:13px;color:var(--muted)}
.criterion{border-bottom:1px solid var(--line);padding:12px 0}.criterion:last-child{border:0}
.criterion-top{display:flex;justify-content:space-between;gap:12px;font-size:17px;font-weight:700}
.criterion p{font-size:14px;color:var(--muted);line-height:1.7;margin:6px 0 0}
.criterion small{font-size:12px;font-weight:400;white-space:nowrap}
.simulation{background:#fff6e6;border:1px solid #e7d5b4;border-radius:14px;padding:18px;margin:0}
.sim-tag{font-size:14px;color:#7a5829;margin-bottom:12px;font-weight:650}
.sim-row{display:flex;justify-content:space-between;gap:12px;align-items:baseline;color:#654c24;font-size:15px;line-height:1.8}
.sim-row strong{font-size:27px;white-space:nowrap}.sim-row small{font-size:14px;font-weight:400}
.sim-row span{flex:1;min-width:0}.sim-row strong{flex-shrink:0}
.sim-foot{font-size:13px;color:#765d38;margin-top:10px;line-height:1.7}
.note-summary{padding:18px;background:#edf1e8;border:1px solid var(--line);border-radius:14px;line-height:1.85;font-size:16px}
.draft-label{font-size:13px;color:#7c5d30;margin-bottom:8px;font-weight:650}
.footer{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:13px;line-height:1.7}
@media(max-width:550px){.block-container{padding:1rem 1rem 1.5rem}.masthead{margin-bottom:12px}.work-title{font-size:21px!important}.work-intro{margin-bottom:12px}.hero{padding:16px 18px}.hero-score{font-size:68px}.hero-score small{font-size:18px}.limit{font-size:13px}.stat-label{font-size:12px}.stat-value{font-size:24px}.stat{padding:10px 5px}.sim-row{font-size:14px}.sim-row strong{font-size:25px}}
</style>'''


def fmt(value, cap=100):
    return format_score(Fraction(value), cap, 2)


def calculator(content, root):
    try:
        default_counts = load_history(root, content)[-1]
    except (OSError, ValueError, TypeError, KeyError):
        default_counts = content['observations']['I1']
    st.header('조회수와 좋아요를 바꿔 보세요', anchor=False)
    st.session_state.setdefault('trial_views', str(default_counts['views']))
    st.session_state.setdefault('trial_likes', str(default_counts['likes']))
    st.session_state.setdefault('audience_views', st.session_state['trial_views'])
    st.session_state.setdefault('audience_likes', st.session_state['trial_likes'])
    with st.form('audience_calculation', border=False, enter_to_submit=True):
        views = st.text_input('강의 영상 조회수 (회)', key='audience_views', max_chars=20)
        likes = st.text_input('강의 영상 좋아요 (개)', key='audience_likes', max_chars=20)
        submitted = st.form_submit_button('계산하기', type='primary', width='stretch')
    if submitted:
        st.session_state['trial_views'], st.session_state['trial_likes'] = views, likes
        try:
            st.session_state['trial_result'] = simulate(content, views, likes)
            st.session_state['trial_error'] = False
        except (ValueError,TypeError):
            st.session_state['trial_result'] = None
            st.session_state['trial_error'] = True
    if st.session_state.get('trial_error'):
        st.error('조회수와 좋아요는 0 이상의 정수로 입력해 주세요. 쉼표·소수점·음수는 사용할 수 없습니다.')
    result = st.session_state.get('trial_result')
    if result is not None:
        signed = ('+' if result['delta'] >= 0 else '−') + fmt(abs(result['delta']),10)
        st.markdown(f'''<div class="simulation"><div class="sim-tag">가상 결과</div>
<div class="sim-row"><span>가상 강의 영상 점수</span><strong>{fmt(result['I1'],10)} <small>/ 10점</small></strong></div>
<div class="sim-row"><span>기존 강의 영상 점수와의 차이</span><strong>{signed}<small>점</small></strong></div>
<div class="sim-row"><span>가상 종합 창작성 판단지수</span><strong>{fmt(result['J'])} <small>/ 100점</small></strong></div></div>''', unsafe_allow_html=True)
    st.caption('입력값은 저장하지 않으며 공식 관측 기록에 반영하지 않습니다.')


def score_view(content, root):
    st.markdown('''<div class="stat-grid"><div class="stat"><div class="stat-label">창안구</div><div class="stat-value">3/15</div></div><div class="stat"><div class="stat-label">가사 수용 댓글</div><div class="stat-value">522<small>건</small></div></div><div class="stat"><div class="stat-label">감상 의미 사례</div><div class="stat-value">4<small>개</small></div></div></div>''', unsafe_allow_html=True)
    st.caption('가사 판정 · 공연 댓글 수용 · 강의 감상 사례를 각각 집계했습니다.')
    records = content['records']
    if records:
        first = records[0]
        st.markdown(f'<div class="record"><strong>첫 기록 · {escape(first["date"].replace("-","."))} · {fmt(first["J_exact"])}점</strong><br><span>첫 기준 관측을 보존하고, 이후 강의 영상 반응의 변화를 살펴봅니다.</span></div>', unsafe_allow_html=True)
    if len(records)>=2:
        st.vega_lite_chart(history_chart(records), width='stretch')
    render_history(root, content)
    with st.expander('여섯 가지 평가 기준 자세히 보기'):
        cards=[]
        for metric,label in LABELS.items():
            cards.append(f'<div class="criterion"><div class="criterion-top"><span>{label}</span><span>{fmt(content["scores_exact"][metric],MAX_SCORES[metric])} <small>/ {MAX_SCORES[metric]}점</small></span></div><p>{DESCRIPTIONS[metric]}</p></div>')
        st.markdown(''.join(cards), unsafe_allow_html=True)
        st.caption('가사 수용 498단위는 작성자 수나 독창적 해석 수가 아닙니다. 차트·영상·기존 감상 사례의 평가 범위는 아래 ‘출처와 연구 정보’에서 확인할 수 있습니다.')


def audience_notes(root):
    st.header('연구자의 감상 노트', anchor=False)
    try:
        note=load_note(root)
    except (OSError,ValueError,TypeError,KeyError):
        st.info('감상 노트를 확인할 수 없습니다. 다른 메뉴는 계속 이용할 수 있습니다.')
    else:
        st.markdown(f'<div class="note-summary"><strong>{escape(note["title"])}</strong><br>{escape(note["summary"])}</div>',unsafe_allow_html=True)
        with st.expander('전체 글 읽기'):
            for paragraph in note['paragraphs']:
                st.write(paragraph)
            st.caption('여러 수용 주제를 바탕으로 작성한 독립적인 해설입니다. 개별 댓글 인용이 아니며 지수에 자동 가산되지 않습니다.')
    # An archive will appear only after real, separately approved publication.
    st.link_button('강의 영상에서 생각 나누기 ↗',LECTURE,width='stretch')
    with st.expander('작품 분석 더 읽기'):
        st.write('공개 강의의 서로 다른 15구절 중 ‘내 마음속에 그 사람’, ‘가슴이 뭉클해지고’, ‘세월 가도 영원히’ 세 구절을 창안구로 판단했습니다. 비율 3/15=20%를 기본 20점으로 반영하며, 가사 전체가 창안구라는 뜻은 아닙니다.')
        st.write('공연 댓글에서는 가사의 인용·언급·전용도 수용으로 인정했습니다. T 채택522건을 498개 감상 단위로 정리했으며, 강의 감상의 독립 의미 사례 U=4와는 자료와 집계 단위가 다릅니다.')
        st.write('감상 노트의 부드러운 남성 이미지, 따뜻함과 행복은 일부 시청자의 관점을 토대로 읽어 보는 주제입니다. 장르 전체의 변화나 모든 시청자의 생각을 입증하는 결론은 아닙니다.')


def research_info(content):
    with st.expander('출처와 연구 정보'):
        st.markdown('**평가 범위와 한계**')
        st.write('음원 성과(E1) 6.43점은 2022년 주간 디지털 차트 3건과 2023년 연간 다운로드 차트 1건에 한정한 구성형 평가입니다. 확보한 주차 중 최고는 113위이며 전체 기간 최고라는 뜻은 아닙니다. 미확보 주차를 미진입으로 처리하지 않았습니다.')
        st.write('원곡 영상(E2)은 공식 제공 Art Track의 글로벌 통계입니다. 한국 시청자만의 반응이 아니며 한국 지역 재생 제한·미등록 설정이 있습니다. 좋아요는 이전 참고값보다 1개 감소했으나 원인은 확인되지 않았습니다. 통계 확인과 실제 재생 여부는 별개입니다.')
        st.write('문학적 감상(I2)은 기존 승인 범위의 독립 의미 사례 4개입니다. ‘가사 전체에 대한 감상’ 사례에는 다른 곡의 가사 감상을 포함한 기존 범위 예외가 있습니다. 네 사례 모두가 이 곡의 새로운 직접 해석이라는 뜻은 아니며, 이번 개편은 승인 범위를 바꾸지 않습니다.')
        st.markdown('**첫 관측 자료 · 2026년 10월 18일 03:09 한국시간**')
        for metric,label in (('E2','원곡 공식 제공 영상'),('I1','연세대 강의 영상')):
            row=content['observations'][metric]
            st.markdown(f'[{label}]({row["url"]}) · 조회수 **{row["views"]:,}회** · 좋아요 **{row["likes"]:,}개**')
        for row in content['charts']:
            st.markdown(f'[{row["label"]} · {row["rank"]}위]({row["url"]})')
        st.caption('연간 다운로드 순위와 주간 디지털 지수는 같은 집계가 아니므로 지수를 합산하지 않았습니다.')
        st.markdown('**계산과 수용 판정**')
        st.code('J = B1 + E1 + E2 + E3 + I1 + I2\nB1 = 20\nE1 = 3 + 2×(201−113)/200 + 1 + 2×(201−46)/200 = 6.43\nE2 = 6V/(V+10000000) + 4L/(L+50000)\nE3 = 12nT/(nT+100) + 11nA/(nA+10) + 4cQ/(cQ+40)\nI1 = 6V/(V+125000) + 4L/(L+2500)\nI2 = 25U/(U+2), U=4',language=None,wrap_lines=True)
        st.write('E3: T 채택522건, A 인정11·불인정1, 498단위. nT=492.5, nA=5.5, cQ≈110.5998555546. C는 공연 댓글15,456건의 작성 분기·유형별 좋아요 상대순위를 바탕으로 감상 단위 안의 최대 공감 가중치를 사용합니다.')
        st.write('E3는 직접 인용·언급을 포함한 공연 댓글 수용, I2는 강의 댓글의 독립 의미 사례를 측정합니다. 둘의 차이를 단순히 인용 대 창의적 해석으로 나누지 않습니다.')
        st.caption('표시는 소수 둘째 자리로 반올림합니다. 내부 합산과 체험 계산은 승인된 정확값을 사용합니다. 가상 입력과 감상 노트는 공식 기록·점수에 반영되지 않습니다.')
        st.caption('다음 실제 기록은 검증·사용자 승인·수동 게시 후 추가합니다. 계산식 변경과 실제 수용 증가를 구분하며, 현재 자동 수집과 정기 게시를 운영하고 있지 않습니다.')
        st.markdown('**강의 영상의 실험 목표**')
        st.write('강의 영상 조회수 목표: 500,000회 · 좋아요 목표: 10,000개 · 이때 I1 목표 점수: 8/10점')
        st.caption('실제 관측값이 아닌 목표이며 승인된 포화형 계산식은 그대로 적용합니다.')


def render(root):
    st.markdown(CSS,unsafe_allow_html=True)
    try:
        content=load_content(root)
    except (OSError,ValueError,TypeError,KeyError):
        st.error('승인 자료를 확인할 수 없습니다. 잠시 후 다시 확인해 주세요.')
        return
    support_banner(root)
    st.markdown('''<div class="masthead"><div class="brand">GOKPOP <span>2.0</span></div></div>
<h1 class="work-title">사랑해요 그대를</h1><p class="work-intro">임영웅의 노래를 함께 읽는 대중 참여형 문학 실험</p>''',unsafe_allow_html=True)
    st.markdown(f'''<div class="hero"><div class="score-label">종합 창작성 판단지수</div><div class="hero-score">{fmt(content['J_exact'])}<small>/ 100점</small></div><div class="baseline">2026년 10월 18일 첫 기준 관측</div></div><p class="limit">실험적 지수이며 작품의 절대적인 예술 가치나 순위를 뜻하지 않습니다.</p>''',unsafe_allow_html=True)
    with st.expander('자세히 알아보기'):
        st.write('노래 가사의 창작성, 어떻게 판단할까요?')
        st.write('가사 × 대중의 수용 × 문학적 감상 · 임영웅 〈사랑해요 그대를〉를 대상으로 한 대중 참여형 문학 실험')
        st.write('가사의 표현과 대중의 반응, 문학적 감상을 여섯 가지 기준으로 살펴본 실험적 판단지수입니다.')
        st.write('이 숫자가 노래의 절대적인 예술적 가치나 다른 노래와의 객관적인 순위를 뜻하지는 않습니다. 작품을 함께 읽고, 반응의 변화를 살펴보는 출발점입니다.')
        st.markdown('**강의에서 소개한 공식은 어떻게 확장되었나요?**')
        for paragraph in FORMULA_EXPLANATION:
            st.markdown(paragraph)
    selected=st.segmented_control('보고 싶은 내용',MENUS,default='점수 보기',required=True,key='audience_menu',label_visibility='collapsed',width='stretch')
    if selected=='직접 계산':
        calculator(content, root)
    elif selected=='감상 노트':
        audience_notes(root)
    else:
        score_view(content, root)
    research_info(content)
    st.markdown('<div class="footer">GOKPOP 2.0 · 가사와 대중의 만남</div>',unsafe_allow_html=True)
    performance_video()
