import os
import requests
import schedule
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Keys from .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def get_news():
    """Fetch Top Headlines from NewsAPI with fallback"""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Try India Headlines first
    url_in = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
    
    try:
        response = requests.get(url_in, headers=headers)
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            if articles:
                print(f"Fetched {len(articles)} articles from India.")
                return articles[:10]
            
        # Fallback to World Top Headlines if India is empty
        print("India news empty, trying global headlines...")
        url_world = f"https://newsapi.org/v2/top-headlines?language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url_world, headers=headers)
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            print(f"Fetched {len(articles)} global articles.")
            return articles[:10]
            
        print(f"Error from API: {response.status_code} - {response.text}")
        return []
    except Exception as e:
        print(f"Request failed: {e}")
        return []

def summarize_news(articles):
    """Summarize articles using Gemini"""
    if not articles:
        return "Aaj koi khas news nahi mili."

    # Create a giant string of headlines and descriptions
    news_text = ""
    for i, art in enumerate(articles, 1):
        news_text += f"{i}. {art['title']} - {art.get('description', 'N/A')}\n"

    prompt = f"""
    You are a smart News Summarizer Bot. Below are some of today's top headlines:
    {news_text}
    
    Summarize these into 5-7 interesting bullet points. 
    Make it engaging and easy to read for a morning update. 
    Write in a Mix of Hindi and English (Hinglish) style so it feels friendly.
    Example: '1. Bitcoin ki kimat badh gayi: Ab $100k paar!'
    """
    
    response = model.generate_content(prompt)
    return response.text

def send_to_telegram(text):
    """Send the final summary to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Summary sent successfully to Telegram!")
    else:
        print(f"Error sending message: {response.text}")

def daily_job():
    print("Running Daily News Summarizer Job...")
    news = get_news()
    summary = summarize_news(news)
    
    # Adding a header
    final_message = f"☀️ *Good Morning!* Aaj ki top news updates:\n\n{summary}"
    
    send_to_telegram(final_message)

# Schedule for 7:00 AM (Aap isse change bhi kar sakte hain)
schedule.every().day.at("07:00").do(daily_job)

if __name__ == "__main__":
    print("Bot is starting... (Press Ctrl+C to stop)")
    print(f"Scheduled every day at 07:00 AM. Waiting for next run...")
    
    # For testing, uncomment the line below to run it immediately once
    # daily_job() 

    while True:
        schedule.run_pending()
        time.sleep(60) # Watch every minute
