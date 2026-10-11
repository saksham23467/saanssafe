# SaansSafe — 3-minute demo script

Setup: `uvicorn app:app --port 8000`, browser at http://localhost:8000, zoom 110%. Pre-run Delhi once so data is cached. Before recording, subscribe 2 schools on the Morning alerts tab (e.g. "DPS Rohini / Rohini, Delhi" and "KV Lucknow / Lucknow"), and record in Chrome so a Hindi voice is available (test the Listen button first; if there's no Hindi voice, show the English Listen instead and mention Hindi works on Chrome/Android). Record at 1280×800.

**Live on AWS:** https://us92heu19l.execute-api.ap-south-1.amazonaws.com/ — running on AWS Lambda + API Gateway + EventBridge + DynamoDB + SNS in ap-south-1 (Mumbai). Record the demo on this URL and say so on screen.

| Time | Screen / click | Say | Judging criterion |
|---|---|---|---|
| 0:00–0:12 | Title card, then the empty SaansSafe page | "On severe-air days in Delhi, schools have been ordered shut or moved online. On every other bad-air day, a principal decides alone at 7 AM: assembly outside? sports? what do I tell parents? SaansSafe answers that." | **Impact** (hook) |
| 0:12–0:25 | Point at the headline and the form | "It's for principals and parents in India. It uses India's official CPCB AQI scale, not the US one, and it speaks Hindi." | **Impact / usability** |
| 0:25–0:50 | Type **Delhi**, click **Get today's plan**. Point at the hero card, then the decision card | "Delhi right now: CPCB AQI, category colour, CPCB's health note, and on the right the decision in plain words, plus what to do for children with asthma." (Read the actual headline.) | **Working execution / usability** |
| 0:50–1:05 | Hover the hourly chart; point at the green **safe outdoor window** pill; glance at the 7-day outlook | "It tells you *when* the air is least bad in school hours, so sports move to that slot, and which days this week to plan indoors." | **Usability / impact** |
| 1:05–1:30 | Parent notice: click **▶ सुनें / Listen** on the Hindi notice (let ~4 s play), click **■ Stop**, then **Share on WhatsApp** | "The notice is ready in English and Hindi. Not every parent reads comfortably, so one tap reads it aloud in Hindi, right in the browser. And one tap shares it on WhatsApp." | **Usability for affected people** |
| 1:30–1:45 | Click **District view**, **Rank schools** | "A district officer pastes every locality and sees which schools need an indoor schedule today." | **Impact / scale** |
| 1:45–2:25 | Click **Morning alerts**. (Pre-subscribe 2 schools before recording.) Subscribe one more live, then click **Preview tomorrow's 7 AM alert**. Point at the dark **Amazon EventBridge** badge and `cron(30 1 * * ? *)`, then the generated alert cards and the outbox | "But a principal shouldn't have to remember to check. Subscribe the school once, and every morning at 7 AM IST an **Amazon EventBridge** schedule triggers an **AWS Lambda** job. It reads subscribers from **DynamoDB**, builds each school's plan and Hindi-English notice, and publishes it through **Amazon SNS**. This button runs that exact job now: here's tomorrow's 7 AM alert for each school." | **Built on AWS / working execution** |
| 2:25–2:50 | Editor: `template.yaml` (scroll to `DailyAlertsFunction` → `Schedule: cron(30 1 * * ? *)`, `SubscriptionsTable`, `AlertsTopic`), then `saanssafe/tools.py` `@tool` decorators | "It's all in one SAM template: the schedule, the alert Lambda, the table, the topic. The agent is AWS's open-source **Strands Agents SDK** with six tools, using **Amazon Bedrock** when credentials exist. Rules make the decisions and the model only explains them, so it never invents a number, and with no key it still works." | **Built on AWS** |
| 2:50–3:00 | Back to the Delhi result | "SaansSafe: a clear plan for every school, every morning, before the bell rings. Thank you." | Close |

Tips: show the "Assistant summary" mode label honestly ("deterministic mode" if no key is set, "Strands agent" with Bedrock). Don't quote numbers that aren't on screen.

Never say alerts are *deployed* unless you've actually run `sam deploy`; say "the SAM template deploys it" and "this button runs the same job".
