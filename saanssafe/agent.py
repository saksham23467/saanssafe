"""Strands agent + configurable model provider, with a deterministic no-LLM fallback."""
from __future__ import annotations
import os
from . import core

SYSTEM = """You are SaansSafe, an assistant for Indian school principals and parents on bad-air days.
Always call plan_school_day for the requested place (and draft_parent_notice when a notice is asked for).
Never invent AQI numbers or health statistics: use only tool outputs. Use India's CPCB AQI categories.
Reply in short plain language: 1) today's verdict, 2) what to do with assembly/sports, 3) best outdoor
hours, 4) masks and indoor air, 5) care for children with asthma. Say the hourly values are forecasts."""

def build_model():
    """Bedrock if AWS creds exist; else OpenAI-compatible; else Ollama; else None (fallback)."""
    prov = os.getenv("SAANSSAFE_PROVIDER", "auto").lower()
    has_aws = bool(os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or os.getenv("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI"))
    if prov == "none":
        return None
    if prov == "bedrock" or (prov == "auto" and has_aws):
        from strands.models import BedrockModel
        return BedrockModel(model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-lite-v1:0"),
                            region_name=os.getenv("AWS_REGION", "us-east-1"))
    if prov == "openai" or (prov == "auto" and os.getenv("OPENAI_API_KEY")):
        from strands.models.openai import OpenAIModel
        args = {"api_key": os.getenv("OPENAI_API_KEY")}
        if os.getenv("OPENAI_BASE_URL"): args["base_url"] = os.getenv("OPENAI_BASE_URL")
        return OpenAIModel(client_args=args, model_id=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    if prov == "ollama" or (prov == "auto" and os.getenv("OLLAMA_HOST")):
        from strands.models.ollama import OllamaModel
        return OllamaModel(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                           model_id=os.getenv("OLLAMA_MODEL", "llama3.1"))
    return None

def build_agent(model=None):
    from strands import Agent
    from .tools import ALL_TOOLS
    return Agent(model=model, tools=ALL_TOOLS, system_prompt=SYSTEM, callback_handler=None)

def fallback_summary(rep: dict) -> str:
    p = rep["plan"]; c = p["current"]
    return (f"{rep['label']}: CPCB AQI {c['aqi']} ({c['category']['name']}, dominant {c['dominant']}). "
            f"{p['headline']}. " + " ".join(p["actions"]))

def advise(place: str, school: str = "Our School", start: int = 8, end: int = 14) -> dict:
    """Main entry: the structured report always comes from the deterministic tools; the LLM (if any)
    adds a conversational summary. Any LLM failure falls back to the template, so the demo never breaks."""
    rep = core.full_report(place, school, start, end)
    rep["mode"], rep["summary"] = "fallback", fallback_summary(rep)
    try:
        model = build_model()
    except Exception as e:  # provider lib/creds problem
        model, rep["llm_error"] = None, str(e)
    if model is not None:
        try:
            agent = build_agent(model)
            res = agent(f"School: {school}. Place: {place}. School hours {start}:00-{end}:00. Give today's plan.")
            rep["summary"], rep["mode"] = str(res).strip(), "agent"
        except Exception as e:
            rep["llm_error"] = str(e)[:300]
    return rep

def rank_schools(entries: list[str], start: int = 8, end: int = 14) -> list[dict]:
    rows = []
    for e in entries:
        e = e.strip()
        if not e: continue
        try:
            r = core.full_report(e, e, start, end, with_outlook=False); p = r["plan"]
            rows.append({"query": e, "label": r["label"], "aqi": p["current"]["aqi"],
                         "category": p["current"]["category"]["name"], "color": p["current"]["category"]["color"],
                         "fg": p["current"]["category"]["fg"], "peak": p["peak_school_aqi"], "status": p["status"],
                         "headline": p["headline"], "window": p["safe_window"], "level": p["level"]})
        except Exception as ex:
            rows.append({"query": e, "error": str(ex)})
    return sorted(rows, key=lambda r: (-(r.get("level", -1)), -(r.get("peak") or 0)))

if __name__ == "__main__":
    import sys, json
    r = advise(" ".join(sys.argv[1:]) or "Delhi")
    print(f"[mode={r['mode']}]\n{r['summary']}\n\n{r['notice']['english']}\n\n{r['notice']['hindi']}")
