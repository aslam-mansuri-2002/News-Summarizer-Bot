import os
import requests
import threading
import time
# pyrefly: ignore [missing-import]
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

# PythonAnywhere Proxy (MANDATORY for Free Tier)
PA_PROXIES = {
    "http": "http://proxy.server:3128",
    "https": "http://proxy.server:3128",
}

# BASE_URL for Telegram links
BASE_URL = "http://aslamMansuri2002.pythonanywhere.com"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# Helper to detect environment and use proxy
def get_proxies():
    # Only use proxy if running on PythonAnywhere
    if os.environ.get('PYTHONANYWHERE_DOMAIN'):
        return PA_PROXIES
    return None

def get_news(limit=10):
    """Fetch headlines with Proxy and Global Fallback"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://newsapi.org/v2/top-headlines?country=in&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url, headers=headers, timeout=10, proxies=get_proxies())
        res = response.json()
        articles = res.get('articles', [])
        
        if not articles:
            url_global = f"https://newsapi.org/v2/top-headlines?language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
            res_global = requests.get(url_global, headers=headers, timeout=10, proxies=get_proxies()).json()
            articles = res_global.get('articles', [])
            
        formatted = []
        for art in articles[:limit]:
            formatted.append({
                "title": art['title'],
                "summary": art.get('description', 'Click for AI highlights...'),
                "url": art['url'],
                "image": art.get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'),
                "source": art.get('source', {}).get('name', 'News')
            })
        return formatted
    except Exception as e:
        print(f"News Fetch Error: {e}")
        return []

def extract_full_content(url):
    """Scrape article text with Proxy and Better Extraction"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10, proxies=get_proxies())
        soup = BeautifulSoup(response.text, 'html.parser')
        for s in soup(["script", "style", "nav", "header", "footer", "aside"]): s.extract()
        
        # Try to find the main content block
        main_content = soup.find('article') or soup.find('main') or soup.find('div', class_='article-body')
        paragraphs = main_content.find_all('p') if main_content else soup.find_all('p')
        
        text = "\n\n".join([p.get_text() for p in paragraphs if len(p.get_text()) > 60])
        return text if len(text) > 100 else "Full content extraction failed for this source."
    except Exception as e:
        return f"Extraction Error: {e}"

def ai_summarize_text(text, is_telegram=False):
    """Hinglish Summary with Gemini (WhatsApp Style)"""
    if not text or len(text) < 150: return "Summary unavailable."
    try:
        # Super Strong Hinglish Prompt
        prompt = f"Summarize this news into 3 simple bullet points. Use pure HINGLISH (Mix Hindi and English like a WhatsApp chat). No formal Hindi. No pure English. \n\nArticle: {text[:3000]}"
        response = model.generate_content(prompt, request_options={"timeout": 25})
        return response.text.replace('*', '').strip() # Clean bullets
    except:
        return "AI Summary unavailable."

def send_to_telegram(news_items):
    """Send clean Hinglish updates to Telegram"""
    try:
        header = "✨ *AAJ KI KHABREIN (Hinglish)* ✨\n\n"
        full_message = header
        
        for i, item in enumerate(news_items[:3], 1): # Limit to top 3 for clarity
            # Get short summary
            content = extract_full_content(item['url'])
            summary = ai_summarize_text(content, is_telegram=True)
            
            # Formatting for Telegram
            full_message += f"🔔 *{item['title']}*\n"
            full_message += f"{summary}\n\n"
            full_message += f"🔗 [Poora Padhein]({BASE_URL}/article?url={item['url']})\n"
            full_message += "----------------------------\n\n"
            
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": full_message, "parse_mode": "Markdown"}
        requests.post(url, json=payload, proxies=get_proxies(), timeout=25)
    except Exception as e:
        print(f"Telegram error: {e}")

@app.route('/test-telegram')
def test_telegram_route():
    """Trigger manual Hinglish update"""
    news = get_news(limit=2)
    if news:
        send_to_telegram(news)
        return "<h1>Success! Telegram check karein.</h1>"
    return "<h1>No News found.</h1>"

@app.route('/')
def index():
    news_items = get_news()
    return render_template('index.html', news=news_items)

@app.route('/article')
def article():
    target_url = request.args.get('url')
    if not target_url: return "Invalid URL", 400
    full_text = extract_full_content(target_url)
    ai_summary = ai_summarize_text(full_text)
    return render_template('article.html', content=full_text, summary=ai_summary, original_url=target_url)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query: return index()
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
    try:
        articles = requests.get(url, timeout=10, proxies=get_proxies()).json().get('articles', [])
        formatted = [{"title": a['title'], "summary": a.get('description', ''), "url": a['url'], "image": a.get('urlToImage', ''), "source": a.get('source', {}).get('name', 'News')} for a in articles]
        return render_template('index.html', news=formatted)
    except: return index()

def hourly_telegram_job():
    while True:
        try:
            news = get_news(limit=5)
            if news:
                send_to_telegram(news)
        except: pass
        time.sleep(3600)

# Start background job
if not os.environ.get("WERKZEUG_RUN_MAIN"):
    threading.Thread(target=hourly_telegram_job, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
