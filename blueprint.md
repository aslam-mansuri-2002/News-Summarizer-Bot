# News Summarizer Bot - Project Blueprint

Yeh document News Summarizer Bot ke structure aur working ko explain karta hai.

## 1. Project Goal
Roz subha (6:00 AM - 7:00 AM) news ko fetch karna, AI (Gemini) se summarize karwana, aur WhatsApp par bhej dena.

## 2. Tech Stack
- **Language:** Python 3.x
- **News Source:** NewsAPI.org (Free for Developers)
- **AI Model:** Google Gemini API (Summarization ke liye)
- **Messaging:** WhatsApp Cloud API (Meta)
- **Scheduling:** `apscheduler` ya `schedule` library

## 3. Architecture Phase-wise

### Phase 1: News Data Fetching
- Ek script jo NewsAPI se 'Top Headlines' fetch karegi.
- Hum categories set kar sakte hain (e.g., Technology, Business, Sports).

### Phase 2: AI Summarization
- Fetch ki gayi news headlines aur descriptions ko Gemini AI ke paas bheja jayega.
- AI ek structured summary banayega bullet points mein.

### Phase 3: WhatsApp Integration
- Meta Developer Portal par App setup karke WhatsApp API use karenge.
- Python script `requests` library se message bhejegi.

### Phase 4: Automation (Scheduling)
- Script ko roz subha trigger karne ka system (Local PC or Cloud).

## 4. Setup Tasks (To-Do)
- [ ] Get NewsAPI Key (newsapi.org)
- [ ] Get Gemini API Key (aistudio.google.com)
- [ ] Setup Meta Developer Account for WhatsApp API
- [ ] Write Python Script
- [ ] Deploy & Test
