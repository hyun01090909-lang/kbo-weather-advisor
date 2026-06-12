"""
kma_weather.py
-----------------------------------
기상청 공공데이터포털 OpenAPI 호출 모듈
- 단기예보 (getVilageFcst): 기온, 강수확률, 강수량, 풍속, 풍향, 습도, 하늘상태
- 기상특보 (getWthrWrnList): 호우/태풍/강풍 등 특보 발령 여부
- 중기예보 (getMidLandFcst): 3~10일 날씨 전망

Python(서버)에서 호출하므로 CORS 문제 없음.
"""

import re
import datetime
import requests

API_KEY = "b6a3b64d9bc88123255fbcf3a4e4da17410025301c3f46ea77dc5e4243c5dc20"

SHORT_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
WARN_URL  = "http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList"
MID_URL   = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"


# ---------------- 유틸 ----------------
def parse_pcp(v):
    """강수량 문자열 -> float(mm). '강수없음'->0, '1mm 미만'->0.3"""
    if not v or v in ("강수없음", "-"):
        return 0.0
    if v == "1mm 미만":
        return 0.3
    m = re.search(r"([\d.]+)", str(v))
    return float(m.group(1)) if m else 0.0


def now_kst():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=9)


def get_base_datetime():
    """단기예보 발표 시각 계산 (02,05,08,11,14,17,20,23시 + 10분 지연)"""
    kst = now_kst()
    slots = [2, 5, 8, 11, 14, 17, 20, 23]
    base_hour, day_offset = 23, -1
    cur_min = kst.hour * 60 + kst.minute
    for h in slots:
        if cur_min >= h * 60 + 10:
            base_hour, day_offset = h, 0
    base_date = (kst + datetime.timedelta(days=day_offset)).strftime("%Y%m%d")
    return base_date, f"{base_hour:02d}00"


def get_mid_tmfc():
    """중기예보 발표 시각 (06시/18시)"""
    kst = now_kst()
    t = "1800" if kst.hour >= 18 else ("0600" if kst.hour >= 6 else "1800")
    d = kst.strftime("%Y%m%d") if kst.hour >= 6 else \
        (kst - datetime.timedelta(days=1)).strftime("%Y%m%d")
    return d + t


def target_date(day_offset):
    return (now_kst() + datetime.timedelta(days=day_offset)).strftime("%Y%m%d")


# ---------------- 단기예보 ----------------
def fetch_short_term(nx, ny, day_offset=0, timeout=10):
    """단기예보 조회 -> 경기시간(18~22시) 통계 + 시간대별 데이터 반환"""
    base_date, base_time = get_base_datetime()
    params = {
        "serviceKey": API_KEY, "dataType": "JSON", "numOfRows": "1000",
        "pageNo": "1", "base_date": base_date, "base_time": base_time,
        "nx": nx, "ny": ny,
    }
    r = requests.get(SHORT_URL, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    header = data["response"]["header"]
    if header["resultCode"] != "00":
        raise RuntimeError(f"기상청 단기예보 오류: {header['resultMsg']}")

    items = data["response"]["body"]["items"]["item"]
    tdate = target_date(day_offset)

    # 카테고리별 수집
    game = {}        # 경기시간(18~22시)
    hourly = {}      # 시간대별 (14~23시)
    rain_start = None
    for it in items:
        if it["fcstDate"] != tdate:
            continue
        hr = int(it["fcstTime"][:2])
        cat = it["category"]
        val = it["fcstValue"]
        if 18 <= hr <= 22:
            game.setdefault(cat, []).append(val)
        if 14 <= hr <= 23:
            hourly.setdefault(hr, {})[cat] = val
        # 강수 시작 시각
        if cat == "PCP" and hr >= 12 and parse_pcp(val) >= 0.3 and rain_start is None:
            rain_start = f"{hr:02d}:00"

    def avg(cat, conv=float):
        vals = [conv(v) for v in game.get(cat, [])]
        return round(sum(vals) / len(vals)) if vals else 0

    def mx(cat, conv=float):
        vals = [conv(v) for v in game.get(cat, [])]
        return max(vals) if vals else 0

    # 하늘상태 최빈값
    skies = [int(v) for v in game.get("SKY", [])]
    sky_mode = max(set(skies), key=skies.count) if skies else 1

    pcp_vals = [parse_pcp(v) for v in game.get("PCP", [])]
    total_rain = round(sum(pcp_vals), 1)
    peak_rain = round(max(pcp_vals), 1) if pcp_vals else 0.0  # 시간당 최대 강수(mm/h)

    # 시간대별 그래프용 (상세 데이터 포함)
    hours_sorted = sorted(hourly.keys())
    hourly_pop  = [int(hourly[h].get("POP", 0))         for h in hours_sorted]
    hourly_tmp  = [float(hourly[h].get("TMP", 0))       for h in hours_sorted]
    hourly_pcp  = [parse_pcp(hourly[h].get("PCP", "강수없음")) for h in hours_sorted]
    hourly_reh  = [int(hourly[h].get("REH", 0))         for h in hours_sorted]
    hourly_wsd  = [round(float(hourly[h].get("WSD", 0))*3.6, 1) for h in hours_sorted]

    return {
        "avg_prob": avg("POP"),
        "total_rain": total_rain,
        "peak_rain": peak_rain,
        "max_wind": round(mx("WSD") * 3.6, 1),
        "wind_deg": avg("VEC"),
        "temp": avg("TMP"),
        "apparent_temp": avg("WCI") if game.get("WCI") else avg("TMP"),
        "humid": avg("REH"),
        "sky": sky_mode,
        "rain_start": rain_start,
        "hours": hours_sorted,
        "hourly_pop": hourly_pop,
        "hourly_tmp": hourly_tmp,
        "hourly_pcp": hourly_pcp,
        "hourly_reh": hourly_reh,
        "hourly_wsd": hourly_wsd,
        "base": f"{base_date[:4]}.{base_date[4:6]}.{base_date[6:]} {base_time[:2]}:{base_time[2:]}",
    }


# ---------------- 기상특보 ----------------
def fetch_alert(stn_id, timeout=10):
    """기상특보 조회 -> 발령 중인 특보 문자열 (없으면 None)"""
    try:
        params = {
            "serviceKey": API_KEY, "dataType": "JSON",
            "numOfRows": "10", "pageNo": "1", "stnId": stn_id,
        }
        r = requests.get(WARN_URL, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        body = data["response"].get("body", {})
        items = body.get("items", {})
        if not items:
            return None
        item = items.get("item")
        if not item:
            return None
        arr = item if isinstance(item, list) else [item]
        titles = [x.get("title", "") for x in arr if x.get("title")]
        return " / ".join(titles) if titles else None
    except Exception:
        return None


MID_TEMP_URL = "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa"

# ---------------- 중기예보 (주간) ----------------
def fetch_weekly_forecast(reg_id, timeout=10):
    """중기 육상예보 + 중기기온 -> 주간예보 리스트 반환
    3~7일후 날씨 (오전/오후 강수확률, 하늘상태, 최저/최고기온)"""
    try:
        tmfc = get_mid_tmfc()
        params_land = {"serviceKey":API_KEY,"dataType":"JSON","numOfRows":"10","pageNo":"1","regId":reg_id,"tmFc":tmfc}
        params_temp = {"serviceKey":API_KEY,"dataType":"JSON","numOfRows":"10","pageNo":"1","regId":reg_id,"tmFc":tmfc}

        r_land = requests.get(MID_URL, params=params_land, timeout=timeout)
        r_temp = requests.get(MID_TEMP_URL, params=params_temp, timeout=timeout)
        r_land.raise_for_status(); r_temp.raise_for_status()

        land_item = r_land.json()["response"]["body"]["items"]["item"]
        temp_item = r_temp.json()["response"]["body"]["items"]["item"]
        land = land_item[0] if isinstance(land_item, list) else land_item
        temp = temp_item[0] if isinstance(temp_item, list) else temp_item

        import datetime
        today = datetime.date.today()
        days_kr = ["월","화","수","목","금","토","일"]

        result = []
        for d in range(3, 8):   # 3일 후 ~ 7일 후
            date = today + datetime.timedelta(days=d)
            day_name = days_kr[date.weekday()]
            date_str = f"{date.month}.{date.day:02d}."

            # 하늘상태 이모지
            def sky_emoji(wf):
                if not wf: return "🌤️"
                if "맑" in wf: return "☀️"
                if "구름많고" in wf and ("비" in wf or "소나기" in wf): return "🌦️"
                if "흐리고" in wf and ("비" in wf or "소나기" in wf): return "🌧️"
                if "구름많음" in wf or "구름많" in wf: return "⛅"
                if "흐림" in wf: return "☁️"
                return "🌤️"

            wf_am = land.get(f"wf{d}Am", "")
            wf_pm = land.get(f"wf{d}Pm", "")
            rnst_am = land.get(f"rnSt{d}Am", 0)
            rnst_pm = land.get(f"rnSt{d}Pm", 0)
            ta_min = temp.get(f"taMin{d}", "-")
            ta_max = temp.get(f"taMax{d}", "-")

            result.append({
                "day": day_name,
                "date": date_str,
                "emoji_am": sky_emoji(wf_am),
                "emoji_pm": sky_emoji(wf_pm),
                "rain_am": int(rnst_am) if rnst_am else 0,
                "rain_pm": int(rnst_pm) if rnst_pm else 0,
                "t_min": ta_min,
                "t_max": ta_max,
            })
        return result
    except Exception:
        return None


def fetch_mid_forecast(reg_id, timeout=10):
    """중기 육상예보 -> 날씨 전망 텍스트 (3일후 한 줄 요약)"""
    try:
        params = {"serviceKey":API_KEY,"dataType":"JSON","numOfRows":"10","pageNo":"1","regId":reg_id,"tmFc":get_mid_tmfc()}
        r = requests.get(MID_URL, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        item = data["response"]["body"]["items"]["item"]
        it = item[0] if isinstance(item, list) else item
        return it.get("wf3Am") or it.get("wf4Am") or None
    except Exception:
        return None
