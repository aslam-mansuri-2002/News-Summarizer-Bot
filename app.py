import os
import requests
import threading
import time
from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load API Keys
load_dotenv()

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# PythonAnywhere Proxy for Telegram (Free Tier)
PROXIES = {
    "http": "http://proxy.server:3128",
    "https": "http://proxy.server:3128",
}

# BASE_URL for Telegram links
BASE_URL = "http://aslamMansuri2002.pythonanywhere.com"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# Global variable for deduplication
seen_articles = set()

def extract_full_content(url):
    """Fetch and extract main article text"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return "Content not available."
        
        soup = BeautifulSoup(response.text, 'html.parser')
        for s in soup(["script", "style", "nav", "header", "footer", "aside"]): s.extract()
            
        article_body = soup.find('article') or soup.find('main') or soup.find('div', class_='article-body')
        paragraphs = article_body.find_all('p') if article_body else soup.find_all('p')
            
        content = "\n\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 50])
        return content if content else "Full content could not be extracted."
    except Exception as e:
        return f"Error: {e}"

def ai_summarize_text(text):
    """Summarize a single article's text into Hindi"""
    if len(text) < 100: return "Summary not available for short text."
    try:
        prompt = f"Summarize this news article into 3-4 bullet points in HINDI:\n\n{text[:3000]}"
        response = model.generate_content(prompt, request_options={"timeout": 20})
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "AI Summary currently unavailable."

def send_to_telegram(news_items):
    """Send news to Telegram using Proxy"""
    try:
        message = "🚀 *THE NEWS ROOM - LATEST UPDATES*\n\n"
        for i, item in enumerate(news_items, 1):
            internal_link = f"{BASE_URL}/article?url={item['url']}"
            message += f"*{i}. {item['title']}*\n"
            message += f"🔗 [Poora Padhein]({internal_link})\n\n"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        
        # Use proxies only if on PythonAnywhere (detect via environment)
        if "pythonanywhere" in BASE_URL:
            requests.post(url, json=payload, proxies=PROXIES, timeout=10)
        else:
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_news(limit=10):
    """Fetch raw news for fast loading"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://newsapi.org/v2/top-headlines?country=in&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
        articles = res.get('articles', [])
        
        # Format for template
        formatted = []
        for art in articles[:limit]:
            formatted.append({
                "title": art['title'],
                "summary": art.get('description', 'Khabar ki jankari ke liye click karein...'),
                "url": art['url'],
                "image": art.get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'),
                "source": art.get('source', {}).get('name', 'News')
            })
        return formatted
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []

@app.route('/')
def index():
    # Instant load without AI
    news_items = get_news()
    return render_template('index.html', news=news_items, title="🇮🇳 Bharat ki Khabrein")

@app.route('/article')
def article():
    target_url = request.args.get('url')
    if not target_url: return "Invalid URL", 400
    
    # Extract and Summarize ONLY this specific article
    full_text = extract_full_content(target_url)
    ai_summary = ai_summarize_text(full_text)
    
    return render_template('article.html', content=full_text, summary=ai_summary, original_url=target_url)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query: return index()
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
    try:
        articles = requests.get(url, timeout=10).json().get('articles', [])
        formatted = []
        for art in articles:
            formatted.append({
                "title": art['title'],
                "summary": art.get('description', ''),
                "url": art['url'],
                "image": art.get('urlToImage', ''),
                "source": art.get('source', {}).get('name', 'News')
            })
        return render_template('index.html', news=formatted, title=f"Results: {query}")
    except:
        return index()

def hourly_telegram_job():
    while True:
        try:
            news = get_news(limit=5)
            if news:
                send_to_telegram(news)
        except: pass
        time.sleep(3600)

if not os.environ.get("WERKZEUG_RUN_MAIN"):
    threading.Thread(target=hourly_telegram_job, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
