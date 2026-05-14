import os
import requests
import threading
import time
from flask import Flask, render_template, jsonify
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

# BASE_URL for Telegram links (Change this when deploying)
BASE_URL = "http://aslamMansuri2002.pythonanywhere.com"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-flash-latest')

# Global variable for deduplication
seen_articles = set()

def extract_full_content(url):
    """Fetch and extract main article text from the original URL"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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

def send_to_telegram(news):
    """Send Summarized News to Telegram with internal links"""
    try:
        message = "🚀 *THE NEWS ROOM - LATEST UPDATES*\n\n"
        for i, item in enumerate(news, 1):
            internal_link = f"{BASE_URL}/article?url={item['url']}"
            message += f"*{i}. {item['title']}*\n"
            message += f"📝 {item['summary']}\n"
            message += f"🔗 [Poora Padhein]({internal_link})\n\n"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_news(limit=6):
    """Fetch LATEST Top Headlines (Reduced limit for speed)"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://newsapi.org/v2/top-headlines?country=in&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        print(f"Fetching news from NewsAPI (Limit: {limit})...")
        res = requests.get(url, headers=headers, timeout=10).json()
        articles = res.get('articles', [])
        
        if not articles:
            print("India news empty, trying global...")
            url_world = f"https://newsapi.org/v2/top-headlines?language=en&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
            articles = requests.get(url_world, headers=headers, timeout=10).json().get('articles', [])
            
        new_articles = []
        for art in articles:
            title = art.get('title')
            if title and title not in seen_articles:
                new_articles.append(art)
                seen_articles.add(title)
                if len(new_articles) >= limit: break
        
        if len(seen_articles) > 50: seen_articles.clear()
        return new_articles if new_articles else articles[:limit]
    except Exception as e:
        print(f"NewsAPI error: {e}")
        return []

def summarize_for_web(articles):
    if not articles: return []
    print(f"Summarizing {len(articles)} articles with Gemini AI...")
    
    full_prompt = "Summarize the following into HINDI. Headline: [Hindi] Summary: [Hindi] ---\n\n"
    for i, art in enumerate(articles):
        full_prompt += f"Item {i}:\nTitle: {art['title']}\nDescription: {art.get('description', 'N/A')}\n\n"
    
    summarized_list = []
    try:
        # Added 15s timeout to avoid hanging
        response = model.generate_content(full_prompt, request_options={"timeout": 15})
        parts = response.text.split('---')
        for i, part in enumerate(parts):
            if i >= len(articles): break
            lines = part.strip().split('\n')
            h, s = articles[i]['title'], articles[i].get('description', 'विवरण उपलब्ध नहीं है।')
            for line in lines:
                if "Headline:" in line: h = line.replace("Headline:", "").strip()
                if "Summary:" in line: s = line.replace("Summary:", "").strip()
            summarized_list.append({
                "title": h, "summary": s, "url": articles[i].get('url', '#'),
                "image": articles[i].get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'),
                "source": articles[i].get('source', {}).get('name', 'Breaking News')
            })
    except Exception as e:
        print(f"Gemini AI error or timeout: {e}. Using raw news fallback.")
        for art in articles:
            summarized_list.append({
                "title": art['title'], 
                "summary": art.get('description', 'No AI summary available.')[:150] + "...", 
                "url": art.get('url', '#'), 
                "image": art.get('urlToImage', 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=1000'), 
                "source": art.get('source', {}).get('name', 'News')
            })
    return summarized_list

@app.route('/')
def index():
    raw_news = get_news()
    title = "🇮🇳 Bharat ki Sabse Taaza Khabrein"
    news_items = summarize_for_web(raw_news)
    return render_template('index.html', news=news_items, title=title)

@app.route('/article')
def article():
    from flask import request
    url = request.args.get('url')
    if not url: return "Invalid URL", 400
    content = extract_full_content(url)
    return render_template('article.html', content=content, original_url=url)

@app.route('/search')
def search():
    from flask import request
    query = request.args.get('q', '')
    if not query: return index()
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize=12&apiKey={NEWS_API_KEY}"
    try:
        raw_news = requests.get(url, timeout=10).json().get('articles', [])
    except:
        raw_news = []
    news_items = summarize_for_web(raw_news)
    return render_template('index.html', news=news_items, title=f"Results: {query}")

def hourly_telegram_job():
    while True:
        try:
            raw_news = get_news(limit=5)
            if raw_news:
                news_items = summarize_for_web(raw_news)
                send_to_telegram(news_items)
        except: pass
        time.sleep(3600)

if not os.environ.get("WERKZEUG_RUN_MAIN"):
    threading.Thread(target=hourly_telegram_job, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
