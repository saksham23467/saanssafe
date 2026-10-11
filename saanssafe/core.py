"""Deterministic core: data fetching (Open-Meteo, no key), CPCB AQI, school-day rules, notices.
These plain functions are wrapped as Strands @tool functions in tools.py and are also
called directly by the no-LLM fallback path, so both paths share the same logic."""
from __future__ import annotations
import json, urllib.parse, urllib.request
from datetime import datetime
from statistics import mean

UA = {"User-Agent": "SaansSafe/1.0 (hackathon project)"}

def _get(url: str, params: dict) -> dict:
    q = urllib.parse.urlencode(params, doseq=True)
    with urllib.request.urlopen(urllib.request.Request(f"{url}?{q}", headers=UA), timeout=20) as r:
        return json.loads(r.read())

# ---------------------------------------------------------------- data
def geocode(place: str) -> dict:
    """Resolve a city/locality name to coordinates (Open-Meteo geocoding). Prefers India."""
    name = place.split(",")[0].strip()
    d = _get("https://geocoding-api.open-meteo.com/v1/search",
             {"name": name, "count": 10, "language": "en", "format": "json"})
    res = d.get("results") or []
    if not res:
        raise ValueError(f"Could not find a place called '{place}'")
    hint = place.lower()
    def score(r):
        s = 0
        if r.get("country_code") == "IN": s += 10
        ctx = [w.strip() for w in hint.split(",")[1:] if w.strip()]
        if any(c in (r.get("admin1") or "").lower() or c in (r.get("admin2") or "").lower() for c in ctx): s += 5
        return s + (r.get("population") or 0) / 1e9
    r = max(res, key=score)
    return {"name": r["name"], "admin1": r.get("admin1", ""), "country": r.get("country", ""),
            "latitude": r["latitude"], "longitude": r["longitude"],
            "timezone": r.get("timezone", "Asia/Kolkata")}

def get_air_quality(lat: float, lon: float, timezone: str = "Asia/Kolkata") -> dict:
    """Hourly PM2.5 / PM10 for the past 1 day and next 5 days (CAMS via Open-Meteo)."""
    d = _get("https://air-quality-api.open-meteo.com/v1/air-quality",
             {"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10",
              "timezone": timezone, "past_days": 1, "forecast_days": 5})
    h = d["hourly"]
    return {"time": h["time"], "pm2_5": h["pm2_5"], "pm10": h["pm10"]}

def get_weather(lat: float, lon: float, timezone: str = "Asia/Kolkata") -> dict:
    """Hourly temperature, humidity, apparent temperature (heat index proxy) + 7-day daily."""
    d = _get("https://api.open-meteo.com/v1/forecast",
             {"latitude": lat, "longitude": lon, "timezone": timezone, "forecast_days": 7,
              "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability",
              "daily": "temperature_2m_max,apparent_temperature_max,precipitation_probability_max"})
    return {"hourly": d["hourly"], "daily": d["daily"]}

def get_outlook_aq(lat: float, lon: float, timezone: str = "Asia/Kolkata") -> dict:
    """Daily mean PM for up to 7 days (CAMS forecast horizon varies, typically ~5 days)."""
    d = _get("https://air-quality-api.open-meteo.com/v1/air-quality",
             {"latitude": lat, "longitude": lon, "hourly": "pm2_5,pm10",
              "timezone": timezone, "forecast_days": 7})
    days: dict = {}
    for t, a, b in zip(d["hourly"]["time"], d["hourly"]["pm2_5"], d["hourly"]["pm10"]):
        if a is None or b is None: continue
        days.setdefault(t[:10], ([], []))
        days[t[:10]][0].append(a); days[t[:10]][1].append(b)
    return {k: (mean(v[0]), mean(v[1])) for k, v in days.items() if len(v[0]) >= 12}

# ---------------------------------------------------------------- CPCB AQI
# CPCB National AQI breakpoints (24-hr average, ug/m3). Source: CPCB "National Air Quality Index" (2014).
CATS = [  # (name, aqi_lo, aqi_hi, color, text-color)
    ("Good", 0, 50, "#009933", "#fff"),
    ("Satisfactory", 51, 100, "#58A618", "#fff"),
    ("Moderate", 101, 200, "#E6C700", "#1b1b1b"),
    ("Poor", 201, 300, "#F28C00", "#1b1b1b"),
    ("Very Poor", 301, 400, "#E02020", "#fff"),
    ("Severe", 401, 500, "#7E0023", "#fff"),
]
BP = {"pm2_5": [0, 30, 60, 90, 120, 250, 380], "pm10": [0, 50, 100, 250, 350, 430, 510]}
HEALTH = {  # CPCB published health-impact statements (paraphrased)
    "Good": "Minimal impact.",
    "Satisfactory": "Minor breathing discomfort to sensitive people.",
    "Moderate": "Breathing discomfort to people with lung disease such as asthma, and to people with heart disease, children and older adults.",
    "Poor": "Breathing discomfort to most people on prolonged exposure.",
    "Very Poor": "Respiratory illness on prolonged exposure.",
    "Severe": "Affects healthy people and seriously impacts those with existing diseases.",
}

def sub_index(pollutant: str, c: float) -> int:
    b = BP[pollutant]
    for i in range(6):
        lo_c, hi_c = b[i], b[i + 1]
        if c <= hi_c or i == 5:
            lo_i, hi_i = CATS[i][1], CATS[i][2]
            c = min(c, hi_c)
            return round(lo_i + (hi_i - lo_i) * (c - lo_c) / (hi_c - lo_c)) if hi_c > lo_c else lo_i
    return 500

def category(aqi: int) -> dict:
    for n, lo, hi, col, fg in CATS:
        if aqi <= hi:
            return {"name": n, "color": col, "fg": fg, "health": HEALTH[n]}
    n, *_ , col, fg = CATS[-1]
    return {"name": "Severe", "color": col, "fg": fg, "health": HEALTH["Severe"]}

def compute_cpcb_aqi(pm2_5: float, pm10: float) -> dict:
    """CPCB AQI = max of PM2.5 and PM10 sub-indices."""
    s25, s10 = sub_index("pm2_5", pm2_5), sub_index("pm10", pm10)
    aqi = max(s25, s10)
    return {"aqi": aqi, "pm2_5": round(pm2_5, 1), "pm10": round(pm10, 1),
            "dominant": "PM2.5" if s25 >= s10 else "PM10", **{"category": category(aqi)}}

# ---------------------------------------------------------------- rules
LEVEL = {c[0]: i for i, c in enumerate(CATS)}

def _now_index(times: list[str], now: datetime) -> int:
    key = now.strftime("%Y-%m-%dT%H:00")
    return times.index(key) if key in times else len(times) // 4

def plan_school_day(aq: dict, wx: dict, school_start: int = 8, school_end: int = 14,
                    now: datetime | None = None) -> dict:
    """Deterministic rules mapping current AQI + hourly forecast to school actions."""
    now = now or datetime.now()
    t, p25, p10 = aq["time"], aq["pm2_5"], aq["pm10"]
    i = _now_index(t, now)
    win = [(a, b) for a, b in zip(p25[max(0, i - 23): i + 1], p10[max(0, i - 23): i + 1]) if a is not None and b is not None]
    cur = compute_cpcb_aqi(mean(x[0] for x in win), mean(x[1] for x in win))  # 24h rolling avg, as CPCB
    # hourly series for the school day ahead (today if before end, else tomorrow)
    day = now.strftime("%Y-%m-%d") if now.hour < school_end else None
    if day is None:
        nxt = [x for x in t if x[:10] > now.strftime("%Y-%m-%d")]
        day = nxt[0][:10] if nxt else t[-1][:10]
    wx_t = wx["hourly"]["time"]; feel = dict(zip(wx_t, wx["hourly"]["apparent_temperature"]))
    hours = []
    for k, ts in enumerate(t):
        if ts[:10] != day or p25[k] is None or p10[k] is None: continue
        h = int(ts[11:13])
        a = compute_cpcb_aqi(p25[k], p10[k])  # indicative hourly index
        hours.append({"time": ts, "hour": h, "aqi": a["aqi"], "category": a["category"]["name"],
                      "color": a["category"]["color"], "feels_like": feel.get(ts),
                      "school": school_start <= h < school_end})
    sch = [x for x in hours if x["school"]]
    def ok(x):
        return x["aqi"] <= 200 and (x["feels_like"] is None or x["feels_like"] < 40)
    # best contiguous outdoor window inside school hours
    best, run = [], []
    for x in sch:
        run = run + [x] if ok(x) else []
        if len(run) > len(best) or (len(run) == len(best) and run and mean(r["aqi"] for r in run) < mean(r["aqi"] for r in best)):
            best = list(run)
    lvl = LEVEL[cur["category"]["name"]]
    peak_sch = max((x["aqi"] for x in sch), default=cur["aqi"])
    lvl = max(lvl, LEVEL[category(peak_sch)["name"]] - 1)  # bump if school hours are forecast worse
    max_feel = max((x["feels_like"] for x in sch if x["feels_like"] is not None), default=None)
    A = {
        0: ("go", "Normal day", "Outdoor assembly and sports can go ahead as usual."),
        1: ("go", "Normal day, watch sensitive children", "Outdoor activities are fine. Let children with asthma take it easy and keep inhalers handy."),
        2: ("caution", "Shorten outdoor time", "Keep assembly short. Move strenuous sports (running, football) to the best window below or indoors. Children with asthma should stay indoors for PE."),
        3: ("indoor", "Move activities indoors", "Hold assembly indoors or in classrooms over the PA. Cancel outdoor sports and PE; do indoor activities instead."),
        4: ("indoor", "Indoor-only day", "No outdoor assembly, sports or PE. Keep windows closed during peak hours, run air purifiers where available, and limit time in corridors and open areas."),
        5: ("closed", "Consider online or hybrid classes", "Follow any Commission for Air Quality Management (CAQM) / GRAP or state directives, which may require suspending physical classes for some grades. If open, keep everyone indoors all day."),
    }
    status, headline, main = A[lvl]
    actions = [main]
    if best and lvl <= 3:
        actions.append(f"Best outdoor window today: {best[0]['hour']:02d}:00–{best[-1]['hour']+1:02d}:00 (indicative AQI {min(r['aqi'] for r in best)}–{max(r['aqi'] for r in best)}).")
    elif lvl >= 2:
        actions.append("No safe outdoor window during school hours today.")
    if lvl >= 3:
        actions.append("Masks: a well-fitted N95/FFP2 mask during the commute helps older children; cloth or surgical masks give little protection against PM2.5.")
        actions.append("Indoor air: keep doors and windows shut during high-pollution hours, avoid burning anything indoors, and ventilate briefly when outdoor air is better.")
    if lvl >= 2:
        actions.append("Children with asthma or other lung or heart conditions: keep them indoors, ensure they carry reliever inhalers, and ask parents to follow their doctor's action plan. Watch for coughing, wheezing or breathlessness.")
    if max_feel is not None and max_feel >= 40:
        actions.append(f"Heat: feels-like temperature reaches about {round(max_feel)}°C. Avoid outdoor activity at midday, schedule water breaks, and keep ORS available.")
    elif max_feel is not None and max_feel >= 35:
        actions.append(f"Warm day (feels like up to {round(max_feel)}°C): schedule water breaks.")
    return {"current": cur, "status": status, "headline": headline, "actions": actions,
            "day": day, "hours": hours, "safe_window": [best[0]["hour"], best[-1]["hour"] + 1] if best and lvl <= 3 else None,
            "peak_school_aqi": peak_sch, "max_feels_like": max_feel, "level": lvl}

def draft_parent_notice(school: str, place: str, plan: dict) -> dict:
    """Ready-to-send bilingual (English + Hindi) parent notice from the plan."""
    c = plan["current"]; cat = c["category"]["name"]
    hi_cat = {"Good": "अच्छी", "Satisfactory": "संतोषजनक", "Moderate": "मध्यम", "Poor": "खराब",
              "Very Poor": "बहुत खराब", "Severe": "गंभीर"}[cat]
    d = datetime.strptime(plan["day"], "%Y-%m-%d").strftime("%d %b %Y")
    lvl = plan["level"]
    en_act = {0: "All outdoor activities will go ahead as normal.",
              1: "Outdoor activities will go ahead. Children with asthma should carry their inhalers.",
              2: "Outdoor time will be shortened and strenuous sports moved indoors or to cleaner hours.",
              3: "Assembly, sports and PE will be held indoors.",
              4: "All activities will be held indoors. There will be no outdoor assembly, sports or PE.",
              5: "Please watch for official instructions on online/hybrid classes. If school is open, all activities will be indoors."}[lvl]
    hi_act = {0: "सभी बाहरी गतिविधियाँ सामान्य रूप से होंगी।",
              1: "बाहरी गतिविधियाँ होंगी। दमा (अस्थमा) वाले बच्चे अपना इनहेलर साथ रखें।",
              2: "बाहर का समय कम रखा जाएगा और ज़्यादा मेहनत वाले खेल अंदर या साफ़ हवा वाले समय में होंगे।",
              3: "प्रार्थना सभा, खेल और पीई अंदर ही होंगे।",
              4: "सभी गतिविधियाँ अंदर होंगी। बाहर कोई प्रार्थना सभा, खेल या पीई नहीं होगा।",
              5: "कृपया ऑनलाइन/हाइब्रिड कक्षाओं से जुड़े आधिकारिक निर्देशों पर ध्यान दें। स्कूल खुला रहा तो सभी गतिविधियाँ अंदर होंगी।"}[lvl]
    extra_en = " Please send a well-fitted N95 mask for the commute and keep your child's inhaler in their bag if they have asthma." if lvl >= 3 else ""
    extra_hi = " कृपया आने-जाने के लिए ठीक से फिट होने वाला N95 मास्क भेजें, और अगर बच्चे को दमा है तो इनहेलर बैग में रखें।" if lvl >= 3 else ""
    en = (f"Dear Parents,\nThe air quality in {place} on {d} is '{cat}' (CPCB AQI {c['aqi']}). {en_act}{extra_en}\n"
          f"If your child has coughing, wheezing or breathlessness, please keep them at home and consult a doctor.\n— {school}")
    hi = (f"प्रिय अभिभावक,\n{d} को {place} में वायु गुणवत्ता '{hi_cat}' है (CPCB AQI {c['aqi']})। {hi_act}{extra_hi}\n"
          f"अगर बच्चे को खाँसी, घरघराहट या साँस लेने में तकलीफ़ हो, तो कृपया उसे घर पर रखें और डॉक्टर से सलाह लें।\n— {school}")
    return {"english": en, "hindi": hi}

# ---------------------------------------------------------------- composite
def outlook(lat, lon, tz, wx) -> list[dict]:
    aqd = get_outlook_aq(lat, lon, tz)
    out = []
    for k, day in enumerate(wx["daily"]["time"]):
        feel = wx["daily"]["apparent_temperature_max"][k]
        item = {"date": day, "dow": datetime.strptime(day, "%Y-%m-%d").strftime("%a"), "feels_max": feel}
        if day in aqd:
            a = compute_cpcb_aqi(*aqd[day])
            item.update(aqi=a["aqi"], category=a["category"]["name"], color=a["category"]["color"],
                        fg=a["category"]["fg"], indoor=a["aqi"] > 200 or (feel or 0) >= 40)
        else:
            item.update(aqi=None, category="No forecast", color="#d9d9d9", fg="#555", indoor=(feel or 0) >= 40)
        out.append(item)
    return out

def full_report(place: str, school: str = "Our School", start: int = 8, end: int = 14,
                with_outlook: bool = True) -> dict:
    g = geocode(place)
    aq = get_air_quality(g["latitude"], g["longitude"], g["timezone"])
    wx = get_weather(g["latitude"], g["longitude"], g["timezone"])
    plan = plan_school_day(aq, wx, start, end)
    label = ", ".join(x for x in [g["name"], g["admin1"]] if x)
    rep = {"place": g, "label": label, "plan": plan,
           "notice": draft_parent_notice(school, g["name"], plan)}
    if with_outlook:
        rep["outlook"] = outlook(g["latitude"], g["longitude"], g["timezone"], wx)
    return rep
