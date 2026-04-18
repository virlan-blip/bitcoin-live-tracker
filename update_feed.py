import os
import json
import time
import feedparser
import google.generativeai as genai
from datetime import datetime

# 1. Setup Gemini API using the Secret you added to GitHub
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# Using the fast and cost-effective Flash model
model = genai.GenerativeModel('gemini-1.5-flash-latest')
# 2. Define the Data Sources
RSS_FEEDS = [
    "https://news.google.com/rss/search?q=Bitcoin+trading+investing+when:1h&hl=en-US&gl=US&ceid=US:en",
    "https://cointelegraph.com/rss/tag/bitcoin"
]

def fetch_and_process():
    # 3. Load existing data so we don't process the same news twice
    if os.path.exists('live_data.json'):
        with open('live_data.json', 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Get a list of links we already have
    existing_links = {item['link'] for item in data}
    new_items = []

    # 4. Fetch the raw feeds
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        # Grab the top 3 newest items from each feed to keep API costs down
        for entry in feed.entries[:3]:
            if entry.link not in existing_links:
                new_items.append({
                    'link': entry.link,
                    'raw_title': entry.title,
                    'raw_summary': entry.get('summary', ''),
                    'source': feed.feed.get('title', 'News Source'),
                    # We will stamp the exact time the script runs as the "live" time
                    'timestamp': datetime.utcnow().strftime('%I:%M %p UTC')
                })

    if not new_items:
        print("No new articles found. Exiting.")
        return

    # 5. Process new items through Gemini
    for item in new_items:
        prompt = f"""
        You are a live news editor for a financial website like the BBC or Reuters. 
        Review this raw RSS news item about Bitcoin:
        Title: {item['raw_title']}
        Summary: {item['raw_summary']}

        Write a concise, professional 2-3 sentence update for a live coverage feed. 
        Determine if the news is a 'News' event or an 'Opinion/Analysis'.
        
        Return ONLY a valid JSON object in exactly this format, nothing else (no markdown blocks):
        {{"type": "News" or "Opinion", "headline": "A punchy, short headline", "content": "Your 2-3 sentence professional update."}}
        """
        
        try:
            print(f"Asking Gemini to edit: {item['raw_title']}")
            response = model.generate_content(prompt)
            
            # Clean up the response to ensure it's pure JSON
            res_text = response.text.replace('```json', '').replace('```', '').strip()
            ai_data = json.loads(res_text)
            
            # Map the AI output to our item
            item['type'] = ai_data.get('type', 'News')
            item['headline'] = ai_data.get('headline', item['raw_title'])
            item['content'] = ai_data.get('content', 'Update available. Click the link to read more.')
            
            # Prepend the newest item to the top of our data list
            data.insert(0, item)
            
            # Sleep for 2 seconds to avoid hitting API rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing {item['link']} with Gemini: {e}")
            
    # 6. Keep only the 30 most recent items so the file doesn't get infinitely large
    data = data[:30]
    
    # 7. Save back to the JSON file
    with open('live_data.json', 'w') as f:
        json.dump(data, f, indent=2)
        print("Successfully updated live_data.json")

if __name__ == "__main__":
    fetch_and_process()
