# Building SaansSafe: a Strands agent that tells Indian schools what to do on bad-air days

## The problem
On bad-air days in North India, the question at a school isn't "what is the AQI?" but "do we hold assembly outside, and what do we tell parents?" Severe days in Delhi-NCR have led to official school closures under GRAP, but the many Moderate-to-Very-Poor days in between are left to each principal. I wanted a tool that turns a forecast into a decision and a parent notice, in Hindi too.

## The stack
- **Strands Agents SDK** for the agent: six `@tool` functions (geocode, get_air_quality, get_weather, compute_cpcb_aqi, plan_school_day, draft_parent_notice).
- **Amazon Bedrock** (Nova Lite) as the default model, with OpenAI-compatible and Ollama providers as alternatives via env vars.
- **Open-Meteo** for geocoding, weather and CAMS air-quality forecasts (free, no key).
- **FastAPI** plus a single vanilla-JS page (no build step), with an inline SVG chart.
- **Amazon EventBridge + AWS Lambda + DynamoDB + SNS** for daily 7 AM alerts: a schedule `cron(30 1 * * ? *)` (01:30 UTC is 07:00 IST) runs `run_daily_alerts()`, which reads subscribed schools from DynamoDB and publishes each plan and notice to an SNS topic.
- **Web Speech API** in the browser to read notices aloud in Hindi (`hi-IN`) and English (`en-IN`), with no server or cost.
- **AWS SAM / Lambda (Mangum)** or **App Runner** for deployment.

## Design choice: rules decide, the model explains
An LLM shouldn't decide whether 400 children go outside. The CPCB AQI and the school plan are computed deterministically; the agent calls those tools and writes a friendly summary. The same tool functions also run in a no-LLM fallback, so the app works with no key, and a model error never breaks the page.

## What fought back
- **AQI scales differ.** Most APIs return the US EPA AQI. India's CPCB index uses different breakpoints (PM2.5 "Good" ends at 30 µg/m³ on a 24-hour average), so I implemented the CPCB sub-index interpolation myself and unit-tested the band edges.
- **Geocoding Indian localities.** "Dwarka" resolves to the city in Gujarat before the Delhi neighbourhood. I added India-first ranking plus state/area hints from the text after the comma.
- **Model vs station data.** CAMS is a gridded model, so values can differ from CPCB monitors, and modelled PM10 can spike in dust events. I label hourly values as indicative and document this as a limitation.
- **Hindi notices.** I templated these instead of generating them, so the wording is predictable and reviewable.

- **Cron in UTC.** EventBridge schedules are UTC, so 7 AM IST is `cron(30 1 * * ? *)`. Easy to get wrong by 5.5 hours.
- **Local vs cloud parity.** The store and delivery are small pluggable classes (JSON file/outbox locally, DynamoDB/SNS on AWS), so the "Preview tomorrow's 7 AM alert" button runs the exact job the Lambda runs.
- **Hindi voices vary by device.** The Listen button picks a `hi-IN` voice when one exists and shows a hint otherwise.

## What's next
CPCB/SAMEER station data where it's available, per-school SMS/WhatsApp Business delivery (numbers are already collected), and school-specific schedules (per-period PE timetables).
