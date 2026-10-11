# SaansSafe (सांस सेफ)
**Tagline:** Should the kids play outside today? A Strands-powered agent that turns live air-quality forecasts into a school plan and a bilingual parent notice.

**Track:** Air

**Short description:** On bad-air days, Indian school principals must decide early whether to hold assembly and sports outdoors and what to tell parents. SaansSafe takes a city or locality, pulls live and forecast PM2.5/PM10 and weather, computes India's CPCB AQI, and returns a clear decision: normal, shorten outdoor time, move indoors, or consider online classes. It also shows the safe outdoor window in school hours, mask, indoor-air and asthma precautions, a 7-day outlook for planning indoor days, and a ready-to-send English + Hindi parent notice with one-tap WhatsApp sharing and a **Listen** button that reads the notice aloud in Hindi or English (browser Web Speech API), for parents who prefer audio. A district view ranks many schools so education officers can see who needs an indoor schedule. Schools can **subscribe to a daily 7 AM alert**: an Amazon EventBridge schedule triggers a Lambda job that builds each school's plan and bilingual notice from DynamoDB subscriptions and publishes it via Amazon SNS. Decisions come from deterministic rules, so they're reproducible; the LLM only explains them, and the app still works without any API key.

**AWS tools used:**
- Strands Agents SDK (AWS open source): agent framework, 6 `@tool` functions
- Amazon Bedrock (Amazon Nova Lite by default) as the model provider when AWS credentials exist
- Amazon EventBridge schedule (`cron(30 1 * * ? *)`, 07:00 IST) → AWS Lambda daily-alert job
- Amazon DynamoDB (subscriptions) and Amazon SNS (email alert delivery)
- Deployed live with AWS SAM: AWS Lambda + Amazon API Gateway (HTTP API) in ap-south-1; Dockerfile for AWS App Runner as an alternative

**Live demo:** https://us92heu19l.execute-api.ap-south-1.amazonaws.com/ (AWS Lambda + API Gateway + EventBridge + DynamoDB + SNS, ap-south-1) · **Repo:** https://github.com/saksham23467/saanssafe · **Demo video:** <add link>

## Team

Saksham Bansal, Ronit Ghosh, Ujjwal Kumar, Rahul Agarwal (IIIT Delhi)
