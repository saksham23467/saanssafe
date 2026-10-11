import pytest
from saanssafe import alerts
from saanssafe.core import plan_school_day, draft_parent_notice
from tests.test_core import _fake

def _report(pm):
    aq, wx, now = _fake(pm); p = plan_school_day(aq, wx, now=now)
    return {"label": "Delhi, Delhi", "plan": p, "notice": draft_parent_notice("X", "Delhi", p)}

def test_run_daily_alerts(tmp_path):
    st = alerts.JsonStore(tmp_path)
    alerts.subscribe(st, "DPS Rohini", "Rohini, Delhi", "principal@school.in")
    alerts.subscribe(st, "KV Lucknow", "Lucknow", "98765 43210")
    alerts.subscribe(st, "Broken", "Nowhere")
    def fn(s):
        if s["school"] == "Broken": raise ValueError("Place not found")
        return _report(200 if "Rohini" in s["place"] else 20)
    res = alerts.run_daily_alerts(st, alerts.OutboxDelivery(st), fn)
    assert res["count"] == 3 and res["sent"] == 2 and res["schedule"] == "cron(30 1 * * ? *)"
    a, b, c = res["alerts"]
    assert a["status"] == "indoor" and "Very Poor" in a["subject"] and "बहुत खराब" in a["body"]
    assert a["to"] == "principal@school.in" and b["to"] == "+919876543210" and b["contact_type"] == "whatsapp"
    assert "error" in c
    assert len(st.outbox()) == 2 and st.outbox()[0]["channel"] == "local-outbox"
    prev = alerts.run_daily_alerts(st, alerts.OutboxDelivery(st), fn, dry_run=True)
    assert prev["alerts"][0]["delivery"] == "preview" and len(st.outbox()) == 2

def test_subscribe_validation(tmp_path):
    st = alerts.JsonStore(tmp_path)
    with pytest.raises(ValueError): alerts.subscribe(st, "", "Delhi")
    with pytest.raises(ValueError): alerts.subscribe(st, "S", "Delhi", "not-a-contact")
    s = alerts.subscribe(st, "S", "Delhi"); assert st.delete(s["id"]) and st.list() == []
