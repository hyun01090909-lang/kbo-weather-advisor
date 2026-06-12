"""
kbo_app.py
-----------------------------------
⚾ 오늘 직관 가도 돼? — KBO 직관 종합 판단기 (기상청 API 버전)

기상청 공공데이터포털 OpenAPI(단기예보·특보·중기예보)로
구장별 우천취소 확률을 예측하고, 유체역학 연속방정식 기반
그라운드 배수 시뮬레이션으로 경기 가능 여부를 판단합니다.

실행:  streamlit run kbo_app.py
"""

import os
import streamlit as st
import kma_weather as kma

st.set_page_config(page_title="오늘 직관 가도 돼?", page_icon="⚾", layout="wide")

# ---- KBO 다이아고딕 폰트 로드 ----
import base64
_font_path = os.path.join(os.path.dirname(__file__), "KBO_Dia_Gothic_medium.ttf")
if os.path.exists(_font_path):
    with open(_font_path, "rb") as _f:
        _font_b64 = base64.b64encode(_f.read()).decode()
    # Bold 폰트도 로드
    _bold_path = os.path.join(os.path.dirname(__file__), "KBO_Dia_Gothic_bold.ttf")
    _bold_css = ""
    if os.path.exists(_bold_path):
        with open(_bold_path, "rb") as _f2:
            _bold_b64 = base64.b64encode(_f2.read()).decode()
        _bold_css = f"""
      @font-face {{
        font-family: 'KBODia';
        src: url('data:font/truetype;base64,{_bold_b64}') format('truetype');
        font-weight: bold;
      }}"""
    st.markdown(f"""
    <style>
      @font-face {{
        font-family: 'KBODia';
        src: url('data:font/truetype;base64,{_font_b64}') format('truetype');
        font-weight: normal;
      }}
      {_bold_css}
      /* 일반 텍스트: Medium */
      .stApp, .stMarkdown, .stMetric, .stButton, .stSelectbox,
      .stRadio, .stExpander, .stInfo, .stSuccess, .stWarning, .stError,
      [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
      [data-testid="stMarkdownContainer"] p,
      [data-testid="stMarkdownContainer"] div,
      [data-testid="stMarkdownContainer"] span {{
        font-family: 'KBODia', 'Gothic A1', sans-serif !important;
      }}
      /* 제목·강조: Bold */
      h1, h2, h3, h4,
      [data-testid="stMarkdownContainer"] h1,
      [data-testid="stMarkdownContainer"] h2,
      [data-testid="stMarkdownContainer"] h3,
      [data-testid="stMarkdownContainer"] strong,
      [data-testid="stMarkdownContainer"] b,
      [data-testid="stMetricValue"] {{
        font-family: 'KBODia', 'Gothic A1', sans-serif !important;
        font-weight: bold !important;
      }}
    </style>
    """, unsafe_allow_html=True)

# ---------------- KBO 팀 데이터 ----------------
TEAMS = [
    {"id":"lg",     "name":"LG 트윈스",     "badge":"LG",  "loc":"잠실 야구장",          "color":"#c30452","nx":62,"ny":126,"stn":108,"reg":"11B10101","dome":False,"sp":"손주영",
     "addr":"서울 송파구 올림픽로 25", "lat":37.5121,"lon":127.0719,"map":"https://maps.kakao.com/?q=잠실야구장"},
    {"id":"doosan", "name":"두산 베어스",   "badge":"두산","loc":"잠실 야구장",          "color":"#131230","nx":62,"ny":126,"stn":108,"reg":"11B10101","dome":False,"sp":"곽빈",
     "addr":"서울 송파구 올림픽로 25", "lat":37.5121,"lon":127.0719,"map":"https://maps.kakao.com/?q=잠실야구장"},
    {"id":"kiwoom", "name":"키움 히어로즈", "badge":"키움","loc":"고척 스카이돔",        "color":"#820024","nx":58,"ny":125,"stn":108,"reg":"11B10101","dome":True, "sp":"후라도",
     "addr":"서울 구로구 경인로 430", "lat":37.4982,"lon":126.8672,"map":"https://maps.kakao.com/?q=고척스카이돔"},
    {"id":"ssg",    "name":"SSG 랜더스",    "badge":"SSG", "loc":"인천 SSG 랜더스필드",  "color":"#ce0e2d","nx":54,"ny":124,"stn":112,"reg":"11B20201","dome":False,"sp":"앤더슨",
     "addr":"인천 미추홀구 매소홀로 618", "lat":37.4370,"lon":126.6932,"map":"https://maps.kakao.com/?q=SSG랜더스필드"},
    {"id":"kt",     "name":"KT 위즈",       "badge":"KT",  "loc":"수원 KT위즈파크",      "color":"#000000","nx":60,"ny":121,"stn":119,"reg":"11B20601","dome":False,"sp":"고영표",
     "addr":"경기 수원시 장안구 경수대로 893", "lat":37.2997,"lon":127.0096,"map":"https://maps.kakao.com/?q=KT위즈파크"},
    {"id":"hanwha", "name":"한화 이글스",   "badge":"한화","loc":"대전 한화생명 볼파크", "color":"#fc4e00","nx":67,"ny":100,"stn":133,"reg":"11C20401","dome":False,"sp":"폰세",
     "addr":"대전 중구 대종로 373", "lat":36.3174,"lon":127.4292,"map":"https://maps.kakao.com/?q=한화생명볼파크"},
    {"id":"samsung","name":"삼성 라이온즈", "badge":"삼성","loc":"대구 삼성라이온즈파크","color":"#074ca1","nx":89,"ny":90, "stn":143,"reg":"11H10701","dome":False,"sp":"원태인",
     "addr":"대구 수성구 야구전설로 1", "lat":35.8410,"lon":128.6817,"map":"https://maps.kakao.com/?q=삼성라이온즈파크"},
    {"id":"kia",    "name":"KIA 타이거즈",  "badge":"KIA", "loc":"광주 기아챔피언스필드","color":"#ea0029","nx":58,"ny":74, "stn":156,"reg":"11F20501","dome":False,"sp":"네일",
     "addr":"광주 북구 서림로 10", "lat":35.1681,"lon":126.8889,"map":"https://maps.kakao.com/?q=기아챔피언스필드"},
    {"id":"nc",     "name":"NC 다이노스",   "badge":"NC",  "loc":"창원 NC파크",          "color":"#315288","nx":90,"ny":77, "stn":155,"reg":"11H20101","dome":False,"sp":"하트",
     "addr":"경남 창원시 마산회원구 삼호로 63", "lat":35.2225,"lon":128.5823,"map":"https://maps.kakao.com/?q=NC파크"},
    {"id":"lotte",  "name":"롯데 자이언츠", "badge":"롯데","loc":"부산 사직 야구장",     "color":"#041e42","nx":98,"ny":76, "stn":159,"reg":"11H20201","dome":False,"sp":"반즈",
     "addr":"부산 동래구 사직로 45", "lat":35.1940,"lon":129.0615,"map":"https://maps.kakao.com/?q=사직야구장"},
]

DRAIN_RATE = 30
FLOOD_THRESHOLD = 10

def simulate_drainage(rain_rate, duration_min=180):
    depth, flood = 0.0, None
    dr, rr = DRAIN_RATE/60, rain_rate/60
    for t in range(1, duration_min+1):
        depth = max(0, depth + rr - dr)
        if depth >= FLOOD_THRESHOLD and flood is None:
            flood = t
    return round(depth,1), flood, round(rain_rate-DRAIN_RATE,1)

def cancel_probability(avg_prob, total_rain, max_wind, peak_rain):
    stat = avg_prob*0.45 + min(total_rain/8,1)*25
    depth, flood, net = simulate_drainage(peak_rain)
    if flood is not None:
        phys = 30 - min(flood/180,1)*15 + min(depth/30,1)*10
    else:
        phys = min(net*0.5,8) if net>0 else 0
    wind = 12 if max_wind>45 else (6 if max_wind>35 else 0)
    return min(round(stat+phys+wind),98)

def comfort_score(temp, humid, wind):
    s = 100
    if temp<10: s -= (10-temp)*3.2
    elif temp>28: s -= (temp-28)*3
    elif temp<18: s -= (18-temp)*1.2
    if humid>70: s -= (humid-70)*0.6
    if wind>30: s -= (wind-30)*0.5
    return max(0, min(100, round(s)))

def get_sunset(lat, lon):
    """위경도 기반 일몰 시각 계산 (외부 라이브러리 없이 천문학 공식 사용)"""
    import math, datetime
    today = datetime.date.today()
    day_of_year = today.timetuple().tm_yday
    # 태양 적위
    decl = math.radians(23.45 * math.sin(math.radians(360/365*(day_of_year-81))))
    lat_r = math.radians(lat)
    # 일몰 시각각(hour angle)
    cos_ha = -math.tan(lat_r) * math.tan(decl)
    cos_ha = max(-1, min(1, cos_ha))
    ha = math.degrees(math.acos(cos_ha))
    # UTC 일몰 시각 (시간)
    sunset_utc = 12 + ha/15 - lon/15
    # KST (UTC+9)
    sunset_kst = sunset_utc + 9
    h = int(sunset_kst)
    m = int((sunset_kst - h) * 60)
    return f"{h:02d}:{m:02d}"

def wind_dir(deg):
    return ["북","북동","동","남동","남","남서","서","북서"][round(deg/45)%8]

def sky_text(s):
    return {1:"맑음 ☀️",3:"구름많음 ⛅",4:"흐림 ☁️"}.get(s,"")

def verdict(cancel, temp, comfort, dome, alert):
    if dome:
        return "🏟️","돔이라 무조건 직관!","#33b1ff","고척 스카이돔은 실내라 날씨와 무관하게 경기가 열려요."
    if alert and cancel>=40:
        return "⚠️","기상 특보 발령!","#ff8200",f"기상청 특보 발령 중 · 우천취소 확률 {cancel}% — 경기 취소 가능성이 매우 높습니다."
    if cancel>=55:
        return "🏠","집에서 보세요","#ff3b3b",f"우천취소 확률 {cancel}%로 높아요. 환불 신청을 서두르고 중계로 보는 걸 추천!"
    if cancel>=28:
        return "🤔","우산 챙기고 고민","#ffb627",f"취소 확률 {cancel}%. 애매한 날이에요. 출발 전 구단 공지를 확인하세요."
    extra = ""
    if temp>=30: extra=" 다만 더우니 물·햇빛 대비 필수!"
    elif temp<=8: extra=" 다만 쌀쌀하니 따뜻하게 입으세요!"
    return "👍","직관 추천!","#c6ff00",f"취소 확률 {cancel}%로 낮고 날씨도 좋아요. 오늘은 직관 가는 날!{extra}"

st.markdown("""
<style>
  .stApp { background: linear-gradient(180deg,#06121f,#0c1f33); }
  /* Altair/Vega 차트 배경 투명화 (iframe 내부) */
  [data-testid="stArrowVegaLiteChart"],
  [data-testid="stVegaLiteChart"],
  .vega-embed, .vega-embed > div, .marks {
    background-color: transparent !important;
  }
  iframe[title="streamlit_app"] { background-color: transparent !important; }

  .big-title { font-size:46px; font-weight:900; letter-spacing:-1px; }
  .go { color:#c6ff00; }
  .src-badge { display:inline-block; font-size:12px; font-weight:700; color:#ffb627;
    background:#0e2236; border:1px solid #ffffff22; padding:4px 12px; border-radius:8px; }
</style>

<!-- 야구장 배경 그래픽 (조명탑 + 그라운드) -->
<div style="position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden;opacity:0.13">
<svg width="100%" height="100%" viewBox="0 0 1400 900" preserveAspectRatio="xMidYMax meet"
     xmlns="http://www.w3.org/2000/svg">

  <!-- 잔디 그라운드 (외야) -->
  <ellipse cx="700" cy="980" rx="820" ry="480" fill="#1a5c2a" opacity="0.9"/>
  <!-- 내야 다이아몬드 흙 -->
  <ellipse cx="700" cy="900" rx="340" ry="200" fill="#8B6914" opacity="0.7"/>
  <!-- 다이아몬드 라인 -->
  <polygon points="700,640 900,800 700,960 500,800"
           fill="none" stroke="#ffffff" stroke-width="3" opacity="0.8"/>
  <!-- 피처 마운드 -->
  <ellipse cx="700" cy="800" rx="28" ry="18" fill="#a07820" opacity="0.9"/>
  <!-- 홈플레이트 -->
  <polygon points="700,948 715,935 715,922 685,922 685,935"
           fill="#ffffff" opacity="0.9"/>
  <!-- 베이스 -->
  <rect x="890" y="790" width="20" height="20" fill="#ffffff" opacity="0.9" transform="rotate(45,900,800)"/>
  <rect x="690" y="628" width="20" height="20" fill="#ffffff" opacity="0.9" transform="rotate(45,700,638)"/>
  <rect x="490" y="790" width="20" height="20" fill="#ffffff" opacity="0.9" transform="rotate(45,500,800)"/>
  <!-- 파울 라인 -->
  <line x1="700" y1="948" x2="200" y2="300" stroke="#ffffff" stroke-width="2" opacity="0.5"/>
  <line x1="700" y1="948" x2="1200" y2="300" stroke="#ffffff" stroke-width="2" opacity="0.5"/>
  <!-- 외야 펜스 -->
  <path d="M200,310 Q700,50 1200,310" fill="none" stroke="#ffffff" stroke-width="5" opacity="0.6"/>

  <!-- 조명탑 왼쪽 -->
  <!-- 기둥 -->
  <rect x="118" y="100" width="16" height="380" fill="#b0b8c8" opacity="0.9"/>
  <!-- 가로 암 -->
  <rect x="60" y="100" width="132" height="10" fill="#b0b8c8" opacity="0.9"/>
  <rect x="75" y="140" width="102" height="8" fill="#b0b8c8" opacity="0.85"/>
  <rect x="90" y="175" width="72" height="7" fill="#b0b8c8" opacity="0.8"/>
  <!-- 조명 헤드 -->
  <rect x="48" y="82" width="160" height="22" rx="4" fill="#d4dce8" opacity="0.95"/>
  <rect x="63" y="128" width="130" height="16" rx="3" fill="#d4dce8" opacity="0.9"/>
  <rect x="78" y="162" width="100" height="14" rx="3" fill="#d4dce8" opacity="0.85"/>
  <!-- 조명 글로우 -->
  <ellipse cx="128" cy="93" rx="80" ry="25" fill="#fff8e0" opacity="0.4"/>
  <ellipse cx="128" cy="136" rx="65" ry="18" fill="#fff8e0" opacity="0.3"/>

  <!-- 조명탑 오른쪽 -->
  <rect x="1266" y="100" width="16" height="380" fill="#b0b8c8" opacity="0.9"/>
  <rect x="1208" y="100" width="132" height="10" fill="#b0b8c8" opacity="0.9"/>
  <rect x="1223" y="140" width="102" height="8" fill="#b0b8c8" opacity="0.85"/>
  <rect x="1238" y="175" width="72" height="7" fill="#b0b8c8" opacity="0.8"/>
  <rect x="1192" y="82" width="160" height="22" rx="4" fill="#d4dce8" opacity="0.95"/>
  <rect x="1207" y="128" width="130" height="16" rx="3" fill="#d4dce8" opacity="0.9"/>
  <rect x="1222" y="162" width="100" height="14" rx="3" fill="#d4dce8" opacity="0.85"/>
  <ellipse cx="1272" cy="93" rx="80" ry="25" fill="#fff8e0" opacity="0.4"/>
  <ellipse cx="1272" cy="136" rx="65" ry="18" fill="#fff8e0" opacity="0.3"/>

  <!-- 관중석 실루엣 -->
  <path d="M0,420 Q350,320 700,300 Q1050,320 1400,420 L1400,520 L0,520 Z"
        fill="#0d1f35" opacity="0.8"/>
  <!-- 관중석 라인 -->
  <path d="M0,440 Q350,345 700,325 Q1050,345 1400,440"
        fill="none" stroke="#1e3a5f" stroke-width="2" opacity="0.6"/>
  <path d="M0,470 Q350,375 700,355 Q1050,375 1400,470"
        fill="none" stroke="#1e3a5f" stroke-width="2" opacity="0.5"/>
  <path d="M0,500 Q350,405 700,385 Q1050,405 1400,500"
        fill="none" stroke="#1e3a5f" stroke-width="2" opacity="0.4"/>
</svg>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">⚾ 오늘 직관 <span class="go">가도 돼?</span></div>', unsafe_allow_html=True)
st.markdown("응원하는 팀을 고르면 **기상청 공식 날씨**로 우천취소 확률과 직관 추천을 알려드려요.")
st.markdown('<span class="src-badge">📡 데이터 출처: 기상청 공공데이터포털 (data.go.kr)</span>', unsafe_allow_html=True)
st.write("")

col1, col2 = st.columns([2,1])
with col1:
    sel_name = st.selectbox("⚾ 팀 선택", [t["name"] for t in TEAMS], index=0)
with col2:
    day_label = st.radio("📅 날짜", ["오늘","내일","모레"], horizontal=True)
day_offset = {"오늘":0,"내일":1,"모레":2}[day_label]

team = next(t for t in TEAMS if t["name"]==sel_name)

# ---- 팀별 2색 테마 정의 ----
TEAM_THEMES = {
    "lg":      {"c1":"#C30452","c2":"#C0C0C0","bg1":"#1a0010","bg2":"#0d0008"},  # 검정+빨강
    "doosan":  {"c1":"#131B6B","c2":"#FFFFFF","bg1":"#050818","bg2":"#020410"},  # 네이비+화이트
    "kiwoom":  {"c1":"#820024","c2":"#8C8C8C","bg1":"#180005","bg2":"#0e0003"},  # 자주+회색
    "ssg":     {"c1":"#CE0E2D","c2":"#1A1A1A","bg1":"#1a0005","bg2":"#0d0003"},  # 빨강+검정
    "kt":      {"c1":"#E60012","c2":"#1A1A1A","bg1":"#150003","bg2":"#0a0002"},  # 검정+빨강
    "hanwha":  {"c1":"#FC4E00","c2":"#1A1A1A","bg1":"#1a0d00","bg2":"#0d0700"},  # 주황+검정
    "samsung": {"c1":"#074CA1","c2":"#FFFFFF","bg1":"#020f1f","bg2":"#010810"},  # 파랑+하양
    "kia":     {"c1":"#EA0029","c2":"#D4AF37","bg1":"#180005","bg2":"#0e0003"},  # 빨강+노랑
    "nc":      {"c1":"#1B5E96","c2":"#1A1A1A","bg1":"#020f1a","bg2":"#010a12"},  # 청록+검정
    "lotte":   {"c1":"#002F6C","c2":"#E60026","bg1":"#00060f","bg2":"#000408"},  # 파랑+빨강
}
th = TEAM_THEMES.get(team["id"], {"c1":"#c6ff00","c2":"#33b1ff","bg1":"#06121f","bg2":"#0c1f33"})

def hex_to_rgb(h):
    h=h.lstrip('#')
    return int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)

r1,g1,b1 = hex_to_rgb(th["c1"])
r2,g2,b2 = hex_to_rgb(th["c2"])

st.markdown(f"""
<style>
  /* 전체 배경 */
  .stApp, [data-testid="stAppViewContainer"] {{
    background:
      radial-gradient(1400px 700px at 30% -5%,  rgba({r1},{g1},{b1},0.45) 0%, transparent 55%),
      radial-gradient(1000px 600px at 80% 110%, rgba({r2},{g2},{b2},0.20) 0%, transparent 50%),
      radial-gradient(800px  400px at 90% 0%,   rgba({r1},{g1},{b1},0.20) 0%, transparent 60%),
      linear-gradient(180deg, {th['bg1']} 0%, {th['bg2']} 100%) !important;
  }}
  /* 사이드바도 동일 */
  [data-testid="stSidebar"] {{
    background: {th['bg1']} !important;
  }}
  /* metric 카드 테두리 팀컬러 */
  [data-testid="metric-container"] {{
    border: 1px solid rgba({r1},{g1},{b1},0.3) !important;
    border-radius: 12px !important;
    background: rgba({r1},{g1},{b1},0.08) !important;
  }}
  /* expander 테두리 */
  [data-testid="stExpander"] {{
    border-color: rgba({r1},{g1},{b1},0.3) !important;
  }}
  /* 스크롤바 */
  ::-webkit-scrollbar-thumb {{ background: rgba({r1},{g1},{b1},0.5); border-radius:4px; }}
</style>
""", unsafe_allow_html=True)

logo_col, info_col = st.columns([1,5])
with logo_col:
    logo_path = f"images/{team['id']}.png"
    logo_shown = False
    if os.path.exists(logo_path):
        try:
            from PIL import Image
            Image.open(logo_path).verify()   # 유효한 이미지인지 먼저 확인
            st.image(logo_path, width=150)
            logo_shown = True
        except Exception:
            pass   # 깨진 파일이면 아래 컬러 배지로 대체
    if not logo_shown:
        st.markdown(f"<div style='width:150px;height:150px;border-radius:20px;background:{team['color']};"
                    f"display:flex;align-items:center;justify-content:center;font-size:36px;"
                    f"font-weight:900;color:#fff'>{team['badge']}</div>", unsafe_allow_html=True)
with info_col:
    st.markdown(f"### {team['name']}")
    st.caption(f"🏟️ {team['loc']} | 📍 {team['addr']}")
    sunset = get_sunset(team["lat"], team["lon"])
    col_map, col_sun = st.columns([2, 1])
    with col_map:
        st.markdown(f"[🗺️ 카카오맵에서 보기]({team['map']})")
    with col_sun:
        st.markdown(f"🌇 오늘 일몰: **{sunset}**")

st.divider()

if team["dome"]:
    st.success("🏟️ **돔이라 무조건 직관!** — 고척 스카이돔은 실내 구장이라 날씨와 무관하게 경기가 열려요.")
    st.stop()

with st.spinner(f"{team['name']} 경기장 날씨를 기상청에서 불러오는 중..."):
    try:
        wx = kma.fetch_short_term(team["nx"], team["ny"], day_offset)
        alert = kma.fetch_alert(team["stn"])
        mid = kma.fetch_mid_forecast(team["reg"]) if day_offset>=2 else None
        ok = True
    except Exception as e:
        ok = False; err = str(e)

if not ok:
    st.error(f"⚠️ 기상청 API 호출 실패: {err}")
    st.info("API 키 또는 인터넷 연결을 확인해주세요.")
    st.stop()

if alert:
    st.error(f"⚠️ **기상 특보 발령** — {alert}")

cancel = cancel_probability(wx["avg_prob"], wx["total_rain"], wx["max_wind"], wx["peak_rain"])
comfort = comfort_score(wx["temp"], wx["humid"], wx["max_wind"])
emoji, title, color, desc = verdict(cancel, wx["temp"], comfort, False, bool(alert))
depth, flood, net = simulate_drainage(wx["peak_rain"])

# ---- 기상청 발표시각 + 새로고침 버튼 ----
ref_col, btn_col = st.columns([4, 1])
with ref_col:
    st.markdown(
        f"<div style='background:#0e2236;border:1px solid #ffffff22;border-radius:10px;"
        f"padding:8px 14px;font-size:13px;font-weight:700;color:#ffb627'>"
        f"📡 기상청 발표시각: {wx['base']} · 데이터 기준: {day_label} 18~22시</div>",
        unsafe_allow_html=True)
with btn_col:
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
st.write("")

# ---- 경기 시간대 날씨 요약 한 줄 ----
wind_note = "강풍" if wx["max_wind"]>=20 else ("약간의 바람" if wx["max_wind"]>=10 else "바람 약함")
rain_note = f"강수확률 {wx['avg_prob']}%" if wx["avg_prob"]>0 else "강수 없음"
st.markdown(
    f"<div style='background:#0a1826;border:1px solid #ffffff18;border-radius:10px;"
    f"padding:12px 16px;font-size:14px;font-weight:700;color:#eaf2ff;margin-bottom:12px'>"
    f"🌡️ {day_label} 18~22시 요약: "
    f"<span style='color:#c6ff00'>{sky_text(wx['sky'])}</span> · "
    f"<span style='color:#ffb627'>{wx['temp']}°</span> · "
    f"<span style='color:#33b1ff'>{rain_note}</span> · "
    f"<span style='color:#8aa0b8'>{wind_note} {wx['max_wind']}km/h</span>"
    f"</div>",
    unsafe_allow_html=True)

st.markdown(
    f"<div style='background:#0e2236;border:1px solid {color}55;border-radius:16px;"
    f"padding:24px;text-align:center;box-shadow:inset 0 0 40px {color}22'>"
    f"<div style='font-size:54px'>{emoji}</div>"
    f"<div style='font-size:30px;font-weight:900;color:{color}'>{title}</div>"
    f"<div style='color:#dfe9f5;margin-top:8px;font-weight:600'>{desc}</div></div>",
    unsafe_allow_html=True)
st.write("")

# ---- 색상 게이지 (초록/노랑/빨강) ----
if cancel >= 55:
    gauge_color = "linear-gradient(90deg,#ff6b6b,#ff3b3b)"
    gauge_text_color = "#ff3b3b"
elif cancel >= 28:
    gauge_color = "linear-gradient(90deg,#ffd166,#ffb627)"
    gauge_text_color = "#ffb627"
else:
    gauge_color = "linear-gradient(90deg,#c6ff00,#6fdc00)"
    gauge_text_color = "#c6ff00"

st.markdown(
    f"<div style='margin-bottom:6px;font-size:15px;font-weight:800'>"
    f"🌧️ 우천취소 예측 확률 ({day_label}): "
    f"<span style='color:{gauge_text_color};font-size:22px'>{cancel}%</span></div>"
    f"<div style='height:18px;border-radius:10px;background:#0a1826;"
    f"border:1px solid #ffffff18;overflow:hidden'>"
    f"<div style='height:100%;width:{cancel}%;background:{gauge_color};"
    f"border-radius:10px;transition:width 1s'></div></div>",
    unsafe_allow_html=True)
st.write("")

c = st.columns(4)
c[0].metric("🌡️ 기온", f"{wx['temp']}°")
c[1].metric("🤔 체감온도", f"{wx['apparent_temp']}°")
c[2].metric("☔ 강수확률", f"{wx['avg_prob']}%")
c[3].metric("💧 강수량", f"{wx['total_rain']}mm")
c2 = st.columns(4)
c2[0].metric("💨 풍속", f"{wx['max_wind']}km/h")
c2[1].metric("💦 습도", f"{wx['humid']}%")
c2[2].metric("🌤️ 하늘", sky_text(wx["sky"]))
c2[3].metric("🧭 풍향", f"{wind_dir(wx['wind_deg'])}풍")

i1, i2 = st.columns(2)
with i1:
    if wx["rain_start"]:
        st.info(f"☔ **강수 시작 예상:** 약 {wx['rain_start']}부터 비 가능성")
    else:
        st.info("☀️ **비 예보 없음**")
with i2:
    wn = "강풍, 뜬공 영향 큼" if wx["max_wind"]>=20 else ("타구에 약간 영향" if wx["max_wind"]>=10 else "잔잔함")
    st.info(f"⚾ **바람:** {wind_dir(wx['wind_deg'])}풍 {wx['max_wind']}km/h — {wn}")

if mid:
    st.info(f"📋 **기상청 중기 날씨 전망:** {mid}")

if wx["hours"]:
    import pandas as pd
    import altair as alt
    hours_label = [f"{h}시" for h in wx["hours"]]

    # ---- 꺾은선 그래프: 강수확률 ----
    st.markdown("#### 📈 시간대별 강수확률 (기상청 단기예보)")
    df_pop = pd.DataFrame({"시간": hours_label, "강수확률(%)": wx["hourly_pop"]})
    line = alt.Chart(df_pop).mark_line(
        point=alt.OverlayMarkDef(filled=True, size=60),
        strokeWidth=2.5, color="#33b1ff"
    ).encode(
        x=alt.X("시간", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
        y=alt.Y("강수확률(%)", scale=alt.Scale(domain=[0,100]),
                axis=alt.Axis(title="강수확률 (%)")),
        tooltip=["시간","강수확률(%)"]
    ).properties(height=200).configure_view(strokeWidth=0).configure_axis(
        labelColor="#8aa0b8", titleColor="#8aa0b8", gridColor="#ffffff11")
    st.altair_chart(line, use_container_width=True)

    # ---- 아이폰 스타일 상세 expander ----
    with st.expander("💧 강수량 상세 보기"):
        df_pcp = pd.DataFrame({"시간": hours_label, "강수량(mm)": wx["hourly_pcp"]})
        st.caption(f"총 강수량: {wx['total_rain']}mm · 강수 시작: {wx['rain_start'] or '없음'}")
        bar = alt.Chart(df_pcp).mark_bar(
            color="#33b1ff", cornerRadiusTopLeft=3, cornerRadiusTopRight=3
        ).encode(
            x=alt.X("시간", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("강수량(mm)", axis=alt.Axis(title="강수량 (mm)")),
            tooltip=["시간","강수량(mm)"]
        ).properties(height=180).configure_view(strokeWidth=0).configure_axis(
            labelColor="#8aa0b8", titleColor="#8aa0b8", gridColor="#ffffff11")
        st.altair_chart(bar, use_container_width=True)

    with st.expander("💦 습도 상세 보기"):
        df_reh = pd.DataFrame({"시간": hours_label, "습도(%)": wx["hourly_reh"]})
        st.caption(f"경기시간 평균 습도: {wx['humid']}%")
        line_reh = alt.Chart(df_reh).mark_line(
            point=alt.OverlayMarkDef(filled=True, size=60),
            strokeWidth=2.5, color="#6fdc00"
        ).encode(
            x=alt.X("시간", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("습도(%)", scale=alt.Scale(domain=[0,100]),
                    axis=alt.Axis(title="습도 (%)")),
            tooltip=["시간","습도(%)"]
        ).properties(height=180).configure_view(strokeWidth=0).configure_axis(
            labelColor="#8aa0b8", titleColor="#8aa0b8", gridColor="#ffffff11")
        st.altair_chart(line_reh, use_container_width=True)

    with st.expander("🌡️ 기온 상세 보기"):
        df_tmp = pd.DataFrame({"시간": hours_label, "기온(°C)": wx["hourly_tmp"]})
        st.caption(f"경기시간 평균 기온: {wx['temp']}° / 체감: {wx['apparent_temp']}°")
        line_tmp = alt.Chart(df_tmp).mark_line(
            point=alt.OverlayMarkDef(filled=True, size=60),
            strokeWidth=2.5, color="#ffb627"
        ).encode(
            x=alt.X("시간", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("기온(°C)", axis=alt.Axis(title="기온 (°C)")),
            tooltip=["시간","기온(°C)"]
        ).properties(height=180).configure_view(strokeWidth=0).configure_axis(
            labelColor="#8aa0b8", titleColor="#8aa0b8", gridColor="#ffffff11")
        st.altair_chart(line_tmp, use_container_width=True)

    with st.expander("💨 풍속 상세 보기"):
        df_wsd = pd.DataFrame({"시간": hours_label, "풍속(km/h)": wx["hourly_wsd"]})
        st.caption(f"경기시간 최대 풍속: {wx['max_wind']}km/h · {wind_dir(wx['wind_deg'])}풍")
        line_wsd = alt.Chart(df_wsd).mark_line(
            point=alt.OverlayMarkDef(filled=True, size=60),
            strokeWidth=2.5, color="#8aa0b8"
        ).encode(
            x=alt.X("시간", sort=None, axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y("풍속(km/h)", axis=alt.Axis(title="풍속 (km/h)")),
            tooltip=["시간","풍속(km/h)"]
        ).properties(height=180).configure_view(strokeWidth=0).configure_axis(
            labelColor="#8aa0b8", titleColor="#8aa0b8", gridColor="#ffffff11")
        st.altair_chart(line_wsd, use_container_width=True)

st.markdown("#### 💧 그라운드 배수 시뮬레이션")
st.caption("연속방정식 dV/dt = 유입유량(강수) − 유출유량(배수)")
d1, d2, d3 = st.columns(3)
d1.metric("⬇️ 강수 유입", f"{wx['peak_rain']}mm/h")
d2.metric("🕳️ 배수 용량", f"{DRAIN_RATE}mm/h")
d3.metric("🌊 3시간 후 수심", f"{depth}mm")

if flood is not None:
    st.error(f"🚨 순유입 +{net}mm/h → 약 **{flood}분** 후 침수, 경기 중단 가능")
elif net > 0:
    st.warning(f"⚠️ 순유입 +{net}mm/h, 서서히 물이 고이나 3시간 내 침수 안 됨")
else:
    st.success(f"✅ 배수가 유입을 감당 (순유입 {net}mm/h) → 그라운드 안전")

water_pct = min(depth/FLOOD_THRESHOLD*100, 100)
st.markdown(
    f"<div style='position:relative;height:60px;background:#0a1826;border:1px solid #ffffff18;"
    f"border-radius:10px;overflow:hidden;margin-top:8px'>"
    f"<div style='position:absolute;bottom:0;left:0;right:0;height:{water_pct}%;"
    f"background:linear-gradient(180deg,#33b1ffaa,#1a6fbf);border-top:2px solid #7fd0ff'></div>"
    f"<div style='position:absolute;left:10px;top:8px;font-weight:900;color:#bfe4ff'>{depth}mm</div>"
    f"</div>", unsafe_allow_html=True)

# ---- 강수 유형별 그라운드 영향 ----
st.markdown("#### 🌧️ 강수 유형별 그라운드 영향 분석")
st.caption("유체역학 기반 — 강수 강도에 따른 토양 침투·표면유출 특성")

pr = wx["peak_rain"]
if pr <= 0:
    rain_type = "강수 없음"
    rain_color = "#c6ff00"
    rain_icon = "☀️"
    rain_fluid = "강수 없음 — 그라운드 표면 건조 상태 유지"
    infil_desc = "토양 침투율 정상, 표면유출 없음"
elif pr <= 3:
    rain_type = "이슬비"
    rain_color = "#33b1ff"
    rain_icon = "🌦️"
    rain_fluid = "모세관 흡수 범위 — 토양이 빗물을 충분히 흡수"
    infil_desc = "침투율 > 강수강도 → 표면유출 없음, 배수 여유 충분"
elif pr <= 15:
    rain_type = "보통 비"
    rain_color = "#33b1ff"
    rain_icon = "🌧️"
    rain_fluid = "표면 유출 시작 구간 — 침투율 한계에 근접"
    infil_desc = "일부 표면유출 발생, 배수시스템이 처리 가능한 범위"
elif pr <= 30:
    rain_type = "강한 비"
    rain_color = "#ffb627"
    rain_icon = "⛈️"
    rain_fluid = "포화 침투율 초과 — 물웅덩이(ponding) 형성 시작"
    infil_desc = "침투율 < 강수강도 → 표면 포화, 물 고임 발생"
else:
    rain_type = "폭우"
    rain_color = "#ff3b3b"
    rain_icon = "🌊"
    rain_fluid = "배수 용량 완전 초과 — 경기 중단 불가피"
    infil_desc = "강수 플럭스가 배수 플럭스를 초과, 침수 진행"

st.markdown(
    f"<div style='background:#0a1826;border:1px solid {rain_color}44;border-radius:12px;padding:16px 18px'>"
    f"<div style='font-size:22px;margin-bottom:8px'>{rain_icon} "
    f"<span style='font-size:16px;font-weight:900;color:{rain_color}'>{rain_type}</span> "
    f"<span style='font-size:13px;color:#8aa0b8'>({pr}mm/h)</span></div>"
    f"<div style='font-size:14px;font-weight:700;color:#eaf2ff;margin-bottom:4px'>{rain_fluid}</div>"
    f"<div style='font-size:12px;color:#8aa0b8'>{infil_desc}</div>"
    f"</div>", unsafe_allow_html=True)
st.write("")

# ---- 습도 & 수증기 농도 분석 ----
st.markdown("#### 💦 습도 & 수증기 농도 분석")
st.caption("대기 중 수증기 압력이 경기 환경에 미치는 영향")

hum = wx["humid"]
temp = wx["temp"]

# 포화수증기압 계산 (Tetens 공식)
import math
e_sat = 6.1078 * 10 ** (7.5 * temp / (237.3 + temp))   # hPa
e_act = e_sat * hum / 100                                  # 실제 수증기압

if hum >= 90:
    hum_label = "매우 높음"
    hum_color = "#ff3b3b"
    hum_desc  = "포화 상태에 근접 — 증발이 거의 없어 젖은 그라운드가 마르지 않음"
    ball_desc = "공이 수분을 흡수해 무거워짐, 투수 그립 불안정"
elif hum >= 75:
    hum_label = "높음"
    hum_color = "#ffb627"
    hum_desc  = "수증기 농도 높음 — 그라운드 건조 속도 느림"
    ball_desc = "공의 비행 궤적에 약간 영향, 투수 그립 주의 필요"
elif hum >= 55:
    hum_label = "적정"
    hum_color = "#c6ff00"
    hum_desc  = "쾌적한 수증기 농도 — 경기 최적 환경"
    ball_desc = "공의 비행 안정적, 그라운드 상태 양호"
else:
    hum_label = "낮음"
    hum_color = "#33b1ff"
    hum_desc  = "건조한 대기 — 빠른 증발로 먼지 발생 가능"
    ball_desc = "투수 손가락 건조로 그립감 저하, 공 표면 건조"

col_h1, col_h2, col_h3 = st.columns(3)
col_h1.metric("💦 상대습도", f"{hum}%", label_visibility="visible")
col_h2.metric("🌡️ 포화수증기압", f"{e_sat:.1f}hPa")
col_h3.metric("💧 실제수증기압", f"{e_act:.1f}hPa")

st.markdown(
    f"<div style='background:#0a1826;border:1px solid {hum_color}44;border-radius:12px;padding:16px 18px;margin-top:10px'>"
    f"<div style='font-size:15px;font-weight:900;color:{hum_color};margin-bottom:6px'>습도 {hum_label} ({hum}%)</div>"
    f"<div style='font-size:13px;color:#eaf2ff;margin-bottom:4px'>🌫️ {hum_desc}</div>"
    f"<div style='font-size:13px;color:#8aa0b8'>⚾ {ball_desc}</div>"
    f"</div>", unsafe_allow_html=True)

st.divider()

st.markdown("""
<div style='font-size:11px;color:#3a5068;line-height:1.8;padding:4px 0'>
💡 날씨는 <b>기상청 공공데이터포털(data.go.kr)</b> OpenAPI에서 실시간 수집합니다 — 단기예보·중기예보·기상특보.
우천취소 확률은 기상청 공식 <b>강수확률·강수량·풍속</b>(통계 모델)과,
유체역학 <b>연속방정식</b>(dV/dt = 유입 − 배수) 기반 그라운드 배수 시뮬레이션(물리 모델)을 결합해 계산합니다.
빗물 유입이 배수 용량(30mm/h)을 넘으면 물이 고이기 시작하고, 침수 기준(10mm)을 넘으면 경기 불가로 판단합니다.
</div>
""", unsafe_allow_html=True)