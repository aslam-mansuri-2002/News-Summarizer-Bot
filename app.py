import os
import requests
from flask import Flask, render_template, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# Load API Keys
load_dotenv()

app = Flask(__name__)

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

def send_to_telegram(summary_items):
    """Send a consolidated summary to Telegram"""
    if not summary_items:
        return

    text = "📰 <b>The News Room</b>\n\n"
    for item in summary_items[:6]: # Top 6 for Telegram
        text += f"• <b>{item['title']}</b>\n{item['summary']}\n<a href='{item['url']}'>पूरा पढ़ें</a>\n\n"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
        print("Summary sent to Telegram!")
    except Exception as e:
        print(f"Telegram error: {e}")

def get_news():
    """Fetch Top Headlines from NewsAPI with fallback"""
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # Try India Headlines first
    url_in = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
    
    try:
        print("Fetching India news...")
        response = requests.get(url_in, headers=headers)
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            if articles:
                return articles[:12]
        
        # Fallback to World Top Headlines
        print("India news empty, fetching global headlines...")
        url_world = f"https://newsapi.org/v2/top-headlines?language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url_world, headers=headers)
        if response.status_code == 200:
            return response.json().get('articles', [])[:12]
            
        return []
    except Exception as e:
        print(f"Request failed: {e}")
        return []

def summarize_for_web(articles):
    """Summarize all articles in a single batch request to avoid rate limits"""
    if not articles:
        return []

    print(f"Summarizing {len(articles)} articles in batch...")
    
    # Construct a single prompt for all articles
    full_prompt = "You are a news bot. Summarize the following news items into HINDI. For each item, give me a 'Headline' and a 'Summary' (2 lines).\n\n"
    for i, art in enumerate(articles):
        full_prompt += f"Item {i}:\nTitle: {art['title']}\nDescription: {art.get('description', 'N/A')}\n\n"
    
    full_prompt += "Format your response strictly as follows for each item:\nHeadline: [Hindi Headline]\nSummary: [Hindi Summary]\n---"

    summarized_list = []
    try:
        response = model.generate_content(full_prompt)
        # Split response by the separator
        parts = response.text.split('---')
        
        for i, part in enumerate(parts):
            if i >= len(articles): break
            
            lines = part.strip().split('\n')
            h = articles[i]['title']
            s = articles[i].get('description', 'विवरण उपलब्ध नहीं है।')
            
            for line in lines:
                if "Headline:" in line:
                    h = line.replace("Headline:", "").strip()
                if "Summary:" in line:
                    s = line.replace("Summary:", "").strip()
            
            summarized_list.append({
                "title": h,
                "summary": s,
                "url": articles[i].get('url', '#'),
                "image": articles[i].get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'),
                "source": articles[i].get('source', {}).get('name', 'Breaking News')
            })
    except Exception as e:
        print(f"Batch Summary Error: {e}")
        # Return raw articles if AI fails
        for art in articles:
            summarized_list.append({
                "title": art['title'],
                "summary": art.get('description', 'No summary available.'),
                "url": art.get('url', '#'),
                "image": art.get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'),
                "source": art.get('source', {}).get('name', 'News')
            })
            
    return summarized_list

def search_news(query):
    """Search for news using a keyword"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=12&apiKey={NEWS_API_KEY}"
    
    try:
        print(f"Searching news for: {query}...")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get('articles', [])
        return []
    except Exception as e:
        print(f"Search failed: {e}")
        return []

@app.route('/')
def index():
    from flask import request
    cat = request.args.get('cat', 'india')
    
    if cat == 'india':
        raw_news = get_news() # Our get_news already tries India first
        title = "🇮🇳 Bharat ki Khabrein"
    else:
        # Fetch only global
        headers = {"User-Agent": "Mozilla/5.0"}
        url_world = f"https://newsapi.org/v2/top-headlines?language=en&apiKey={NEWS_API_KEY}"
        response = requests.get(url_world, headers=headers)
        raw_news = response.json().get('articles', [])[:12] if response.status_code == 200 else []
        title = "🌎 Videsh ki Khabrein"

    news_items = summarize_for_web(raw_news)
    return render_template('index.html', news=news_items, title=title)

@app.route('/search')
def search():
    from flask import request
    query = request.args.get('q', '')
    if not query:
        return index()
        
    raw_news = search_news(query)
    news_items = summarize_for_web(raw_news)
    return render_template('index.html', news=news_items, title=f"Results for: {query}")

@app.route('/api/news')
def api_news():
    raw_news = get_news()
    news_items = summarize_for_web(raw_news)
    return jsonify(news_items)

import threading
import time

# ... (Previous imports)

# Naya Background Function jo har ghante chalega
def hourly_telegram_job():
    while True:
        print("Running Hourly Background Job...")
        try:
            raw_news = get_news()
            news_items = summarize_for_web(raw_news)
            # ---------------------------------------------------------
            # TELEGRAM CONTROL: Niche ki lines ko chalu (Uncomment) ya 
            # band (Comment) karke aap Telegram message control kar sakte hain.
            # ---------------------------------------------------------
            if news_items:
                send_to_telegram(news_items)
            # ---------------------------------------------------------
        except Exception as e:
            print(f"Hourly job error: {e}")
        
        time.sleep(3600) # 1 ghante ka intezar

# Thread ko start karein (Sirf tab jab script run ho)
threading.Thread(target=hourly_telegram_job, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False) # use_reloader=False zaroori hai threads ke liye
