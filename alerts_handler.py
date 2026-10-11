"""AWS Lambda entry for the daily 07:00 IST alert job (EventBridge schedule).
Env: SUBSCRIPTIONS_TABLE (DynamoDB), ALERTS_TOPIC_ARN (SNS, optional)."""
import json
from saanssafe.alerts import run_daily_alerts

def handler(event, context):
    res = run_daily_alerts()
    print(json.dumps({k: v for k, v in res.items() if k != "alerts"}))
    return {"count": res["count"], "sent": res["sent"], "ran_at": res["ran_at"]}
