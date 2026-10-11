"""Strands Agents @tool wrappers around the deterministic core."""
from strands import tool
from . import core

@tool
def geocode(place: str) -> dict:
    """Find latitude, longitude and timezone for an Indian city, locality or school area."""
    return core.geocode(place)

@tool
def get_air_quality(latitude: float, longitude: float, timezone: str = "Asia/Kolkata") -> dict:
    """Get hourly PM2.5 and PM10 (ug/m3) for the past day and next 5 days."""
    return core.get_air_quality(latitude, longitude, timezone)

@tool
def get_weather(latitude: float, longitude: float, timezone: str = "Asia/Kolkata") -> dict:
    """Get hourly temperature, humidity and feels-like temperature, plus a 7-day daily forecast."""
    return core.get_weather(latitude, longitude, timezone)

@tool
def compute_cpcb_aqi(pm2_5: float, pm10: float) -> dict:
    """Compute India's CPCB National AQI and category from PM2.5 and PM10 concentrations."""
    return core.compute_cpcb_aqi(pm2_5, pm10)

@tool
def plan_school_day(place: str, school_start_hour: int = 8, school_end_hour: int = 14) -> dict:
    """Fetch live data for a place and return the deterministic school action plan
    (status, actions, safe outdoor window, hourly indicative AQI)."""
    g = core.geocode(place)
    aq = core.get_air_quality(g["latitude"], g["longitude"], g["timezone"])
    wx = core.get_weather(g["latitude"], g["longitude"], g["timezone"])
    p = core.plan_school_day(aq, wx, school_start_hour, school_end_hour)
    p.pop("hours", None)
    return {"place": g, **p}

@tool
def draft_parent_notice(school_name: str, place: str, school_start_hour: int = 8, school_end_hour: int = 14) -> dict:
    """Draft a ready-to-send parent notice in English and Hindi for today's plan."""
    r = core.full_report(place, school_name, school_start_hour, school_end_hour, with_outlook=False)
    return r["notice"]

ALL_TOOLS = [geocode, get_air_quality, get_weather, compute_cpcb_aqi, plan_school_day, draft_parent_notice]
