import os
import json
import time
import feedparser
from google import genai
from datetime import datetime

# Setup Gemini API using the new modern SDK
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# The absolute best industry sources for fundamental trading & institutional news
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Bitcoin+trading+investing+when:1h&hl=en-US&gl=US&ceid=US:en",
    "https://www.theblock.co/rss.xml",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://cointelegraph.com/rss/tag/bitcoin"
]

def fetch_and_process():
    if os.path.exists('live_data.json'):
        with open('live_data.json', 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    existing_links = {item['link'] for item in data}
    new_items = []

    # Fetch the raw feeds
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:
            if entry.link not in existing_links:
                
                # --- GOOGLE NEWS BUG FIX ---
                # Default to the general feed title
                source_name = feed.feed.get('title', 'Industry Source')
                
                # If it's Google News, extract the actual publisher's name
                if "news.google.com" in url:
                    if hasattr(entry, 'source') and hasattr(entry.source, 'title'):
                        source_name = entry.source.title
                    elif " - " in entry.title:
                        # Fallback: Google News titles often end with " - Publisher Name"
                        source_name = entry.title.rsplit(" - ", 1)[-1]
                # ---------------------------

                new_items.append({
                    'link': entry.link,
                    'raw_title': entry.title,
                    'raw_summary': entry.get('summary', ''),
                    'source': source_name,
                    'timestamp': datetime.utcnow().strftime('%I:%M %p UTC')
                })

    if not new_items:
        print("No new articles found. Exiting.")
        return

    # Process new items through Gemini
    for item in new_items:
        # We instruct the AI to focus on fundamental, evergreen analysis
        prompt = f"""
        You are an expert financial analyst curating content for a professional platform. 
        Review this raw RSS feed item about Bitcoin:
        Title: {item['raw_title']}
        Summary: {item['raw_summary']}

        Write a concise, 2-3 sentence professional summary. Prioritize extracting the fundamental analysis, evergreen insights, and in-depth article context over just reporting trending price movements. Highlight the insights of institutions, traders, and active industry companies.
        
        Determine if the content is 'News' or 'Opinion'.
        
        Return ONLY a valid JSON object in exactly this format, nothing else:
        {{"type": "News" or "Opinion", "headline": "An analytical, professional headline", "content": "Your 2-3 sentence analytical summary."}}
        """
        
        try:
            print(f"Asking Gemini to analyze: {item['raw_title']}")
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            
            res_text = response.text.replace('```json', '').replace('```', '').strip()
            ai_data = json.loads(res_text)
            
            item['type'] = ai_data.get('type', 'News')
            item['headline'] = ai_data.get('headline', item['raw_title'])
            item['content'] = ai_data.get('content', 'Detailed analysis available at the source link.')
            
            data.insert(0, item)
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing {item['link']} with Gemini: {e}")
            
    data = data[:30]
    
    with open('live_data.json', 'w') as f:
        json.dump(data, f, indent=2)
        print("Successfully updated live_data.json")

if __name__ == "__main__":
    fetch_and_process()
