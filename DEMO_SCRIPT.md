# SaansSafe: 3-minute demo script

Live: https://us92heu19l.execute-api.ap-south-1.amazonaws.com/

**0:00–0:20 Hook (Today page, empty state).** "Every winter morning, thousands of Indian principals decide whether children should play outside, often with no data. SaansSafe turns live air quality into that decision in seconds." Point at the 3-step "How it works" strip.

**0:20–1:10 Today.** Click the **Delhi** example chip.
- The big headline is the decision (e.g. "Shorten outdoor time"), with one sentence of reason.
- AQI card: the official CPCB AQI, category, and health note.
- **Safe hours** timeline: each school hour scored, with the safe window outlined in teal.
- **7-day outlook**: which days to plan indoor activities.
- **Parent notice**: English and Hindi. Click **Copy**, show **Share on WhatsApp**, and click **सुनें / Listen** to hear the Hindi.

**1:10–1:40 Districts.** Open **Districts** in the top nav and click **Rank schools**. "District officials see which areas should move indoors first." Click the **Peak** column header to sort and point at the bars.

**1:40–2:25 Morning alerts (AWS moment).** Open **Morning alerts**. Point at the schedule card: "Every day 7:00 AM IST via Amazon EventBridge." Show the subscribed schools (from DynamoDB), then click **Preview tomorrow's 7 AM alert**: the Lambda job builds each school's plan and delivers it through Amazon SNS.

**2:25–2:55 About.** Open **About**: who it's for, the architecture diagram (API Gateway → Lambda → Open-Meteo; EventBridge → Lambda → DynamoDB / SNS; Strands Agents SDK tools), the CPCB AQI table, and honest limitations.

**2:55–3:00 Close.** "SaansSafe: clean decisions for dirty-air days, live on AWS."
