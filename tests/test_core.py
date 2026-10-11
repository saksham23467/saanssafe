from saanssafe.core import compute_cpcb_aqi, sub_index, plan_school_day, draft_parent_notice

def test_breakpoints():
    assert sub_index("pm2_5", 30) == 50 and sub_index("pm2_5", 60) == 100
    assert sub_index("pm10", 100) == 100 and sub_index("pm10", 250) == 200
    assert compute_cpcb_aqi(45, 80)["aqi"] == 80
    assert compute_cpcb_aqi(300, 200)["category"]["name"] == "Severe"
    assert compute_cpcb_aqi(10, 20)["category"]["name"] == "Good"

def _fake(pm25, feel=30):
    from datetime import datetime
    t = [f"2026-11-0{d}T{h:02d}:00" for d in (1, 2) for h in range(24)]
    aq = {"time": t, "pm2_5": [pm25]*48, "pm10": [pm25]*48}
    wx = {"hourly": {"time": t, "apparent_temperature": [feel]*48}}
    return aq, wx, datetime(2026, 11, 2, 7)

def test_plan_levels():
    aq, wx, now = _fake(20); p = plan_school_day(aq, wx, now=now)
    assert p["status"] == "go" and p["safe_window"] == [8, 14]
    aq, wx, now = _fake(200); p = plan_school_day(aq, wx, now=now)
    assert p["status"] == "indoor" and p["safe_window"] is None
    n = draft_parent_notice("X School", "Delhi", p)
    assert "Very Poor" in n["english"] and "बहुत खराब" in n["hindi"]
    aq, wx, now = _fake(20, feel=43); p = plan_school_day(aq, wx, now=now)
    assert any("Heat" in a for a in p["actions"])
