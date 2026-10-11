"""Daily morning alerts: subscriptions store (JSON locally / DynamoDB on AWS),
run_daily_alerts() job, and delivery (local outbox / Amazon SNS)."""
from __future__ import annotations
import json, os, re, threading, uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
SCHEDULE_CRON = "cron(30 1 * * ? *)"  # 01:30 UTC = 07:00 IST, every day
DATA_DIR = Path(os.environ.get("SAANSSAFE_DATA", Path(__file__).resolve().parent.parent / "data"))
_lock = threading.Lock()

def _now():
    return datetime.now(IST).isoformat(timespec="seconds")

def validate_contact(contact: str) -> dict:
    c = (contact or "").strip()
    if not c:
        return {"type": None, "value": None}
    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", c):
        return {"type": "email", "value": c}
    digits = re.sub(r"[\s\-()]", "", c)
    if re.fullmatch(r"\+?\d{10,15}", digits):
        if not digits.startswith("+"):
            digits = "+91" + digits[-10:] if len(digits) == 10 else "+" + digits
        return {"type": "whatsapp", "value": digits}
    raise ValueError("Contact must be an email address or a 10–15 digit phone number")

# ------------------------------------------------------------------ stores
class JsonStore:
    """Subscriptions + outbox as JSON files (local dev / demo)."""
    def __init__(self, root: Path = DATA_DIR):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.subs_f, self.out_f = self.root / "subscriptions.json", self.root / "outbox.json"
    def _r(self, f):
        return json.loads(f.read_text("utf-8")) if f.exists() else []
    def _w(self, f, data):
        tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8"); tmp.replace(f)
    def add(self, sub: dict) -> dict:
        with _lock:
            subs = self._r(self.subs_f); subs.append(sub); self._w(self.subs_f, subs)
        return sub
    def list(self) -> list[dict]:
        return self._r(self.subs_f)
    def delete(self, sid: str) -> bool:
        with _lock:
            subs = self._r(self.subs_f); keep = [s for s in subs if s["id"] != sid]
            self._w(self.subs_f, keep)
        return len(keep) != len(subs)
    def record(self, msg: dict):
        with _lock:
            out = self._r(self.out_f); out.insert(0, msg); self._w(self.out_f, out[:100])
    def outbox(self, limit=20) -> list[dict]:
        return self._r(self.out_f)[:limit]

class DynamoStore:
    """Subscriptions in DynamoDB (AWS path). Table key: id (S)."""
    def __init__(self, table: str):
        import boto3
        self.t = boto3.resource("dynamodb").Table(table)
    def add(self, sub):
        self.t.put_item(Item={k: v for k, v in sub.items() if v is not None}); return sub
    def list(self):
        items, kw = [], {}
        while True:
            r = self.t.scan(**kw); items += r.get("Items", [])
            if "LastEvaluatedKey" not in r: break
            kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
        for i in items:
            for k in ("start", "end"):
                if k in i: i[k] = int(i[k])
        return items
    def delete(self, sid):
        self.t.delete_item(Key={"id": sid}); return True
    def record(self, msg):  # delivery log goes to CloudWatch on AWS
        print(json.dumps({"alert": msg}, ensure_ascii=False))
    def outbox(self, limit=20):
        return []

def get_store():
    table = os.environ.get("SUBSCRIPTIONS_TABLE")
    return DynamoStore(table) if table else JsonStore()

# --------------------------------------------------------------- delivery
class OutboxDelivery:
    name = "local-outbox"
    def __init__(self, store): self.store = store
    def send(self, msg): self.store.record({**msg, "channel": self.name}); return "queued-in-outbox"

class SnsDelivery:
    """Publishes to an SNS topic (email subscriptions confirmed via SNS)."""
    name = "amazon-sns"
    def __init__(self, topic_arn, store):
        import boto3
        self.sns, self.arn, self.store = boto3.client("sns"), topic_arn, store
    def send(self, msg):
        r = self.sns.publish(TopicArn=self.arn, Subject=msg["subject"][:100], Message=msg["body"])
        self.store.record({**msg, "channel": self.name, "sns_message_id": r["MessageId"]})
        return "published"

def get_delivery(store):
    arn = os.environ.get("ALERTS_TOPIC_ARN")
    return SnsDelivery(arn, store) if arn else OutboxDelivery(store)

# -------------------------------------------------------------------- API
def subscribe(store, school: str, place: str, contact: str = "", start: int = 8, end: int = 14) -> dict:
    school, place = (school or "").strip(), (place or "").strip()
    if not school or not place:
        raise ValueError("School name and location are required")
    c = validate_contact(contact)
    sub = {"id": uuid.uuid4().hex[:12], "school": school[:120], "place": place[:120],
           "contact_type": c["type"], "contact": c["value"], "start": int(start), "end": int(end),
           "created_at": _now()}
    return store.add(sub)

def build_alert(sub: dict, report: dict) -> dict:
    p, n = report["plan"], report["notice"]
    c = p["current"]
    win = p.get("safe_window")
    win_txt = f"{win[0]:02d}:00–{win[1]:02d}:00" if win else "none during school hours"
    subject = f"SaansSafe 7 AM: {sub['school']} — AQI {c['aqi']} ({c['category']['name']})"
    body = (f"{p['headline']}\nSafe outdoor window: {win_txt}\n\n"
            + "\n".join(f"- {a}" for a in p["actions"])
            + f"\n\n--- Parent notice (English) ---\n{n['english']}\n\n--- अभिभावक सूचना (हिंदी) ---\n{n['hindi']}")
    return {"subscription_id": sub["id"], "school": sub["school"], "place": report.get("label", sub["place"]),
            "to": sub.get("contact"), "contact_type": sub.get("contact_type"), "subject": subject, "body": body,
            "aqi": c["aqi"], "category": c["category"]["name"], "color": c["category"]["color"],
            "status": p["status"], "headline": p["headline"], "safe_window": win,
            "notice": n, "created_at": _now()}

def run_daily_alerts(store=None, delivery=None, report_fn=None, dry_run: bool = False) -> dict:
    """The scheduled job (EventBridge → Lambda at 07:00 IST). Builds each subscriber's
    plan + bilingual notice and delivers it. One bad subscription never stops the rest."""
    store = store or get_store()
    if report_fn is None:
        from saanssafe.core import full_report
        report_fn = lambda s: full_report(s["place"], s["school"], s.get("start", 8), s.get("end", 14), with_outlook=False)
    delivery = delivery or get_delivery(store)
    results = []
    for sub in store.list():
        try:
            alert = build_alert(sub, report_fn(sub))
            alert["delivery"] = "preview" if dry_run else delivery.send(alert)
            results.append(alert)
        except Exception as e:
            results.append({"subscription_id": sub.get("id"), "school": sub.get("school"),
                            "place": sub.get("place"), "error": str(e)[:200]})
    return {"ran_at": _now(), "schedule": SCHEDULE_CRON, "schedule_ist": "Every day 07:00 IST",
            "channel": getattr(delivery, "name", "?"), "dry_run": dry_run,
            "count": len(results), "sent": sum(1 for r in results if "error" not in r), "alerts": results}
