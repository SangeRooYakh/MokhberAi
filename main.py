import os
import requests
import feedparser
import json
import random # <-- IMPORTED FOR RANDOM SELECTION
from bs4 import BeautifulSoup

# --- Configuration ---
# 1. GITHUB SECRETS: Set these in your repository's Settings > Secrets and variables > Actions
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

# 2. OPENROUTER APP IDENTIFICATION: Required by the API.
YOUR_SITE_URL = "https://github.com/SangeRooYakh/MokhberAi"
YOUR_APP_NAME = "Farsi Science News by AI"

# 3. SOURCE LIST: Updated with your new list of Nature feeds.
SOURCES = {
    'Nature Agriculture': {
        'url': 'https://www.nature.com/subjects/agriculture/ncomms.rss',
        'category_fa': 'کشاورزی',
        'hashtag_en': '#Agriculture'
    },
    'Nature Neuroscience': {
        'url': 'https://www.nature.com/subjects/neuroscience/ncomms.rss',
        'category_fa': 'علوم_اعصاب',
        'hashtag_en': '#Neuroscience'
    },
    'Nature Microbiology': {
        'url': 'https://www.nature.com/subjects/microbiology/ncomms.rss',
        'category_fa': 'میکروبیولوژی',
        'hashtag_en': '#Microbiology'
    },
    'Nature Cell Biology': {
        'url': 'https://www.nature.com/subjects/cell-biology/ncomms.rss',
        'category_fa': 'زیست‌شناسی_سلولی',
        'hashtag_en': '#CellBiology'
    },
    'Nature Environmental Sciences': {
        'url': 'https://www.nature.com/subjects/environmental-sciences/ncomms.rss',
        'category_fa': 'علوم_محیط‌زیست',
        'hashtag_en': '#EnvironmentalScience'
    },
    'Nature Ecology': {
        'url': 'https://www.nature.com/subjects/ecology/ncomms.rss',
        'category_fa': 'بوم‌شناسی',
        'hashtag_en': '#Ecology'
    }
}

POSTED_LINKS_FILE = 'posted_links.txt'

# --- Utility Functions (No changes needed here) ---

def load_posted_links():
    try:
        with open(POSTED_LINKS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    except FileNotFoundError:
        return set()

def save_posted_links(links):
    with open(POSTED_LINKS_FILE, 'w', encoding='utf-8') as f:
        for link in sorted(links):
            f.write(link + '\n')

# --- Core Functions (Scraping & AI - No changes needed here) ---

def scrape_article_text(url):
    """Fetches and extracts the main article text from a URL."""
    print(f"  Scraping article text from: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        article_body = soup.find('div', class_='c-article-body')
        if not article_body:
            print("  Could not find main article body for Nature. Scraping failed.")
            return None
        paragraphs = article_body.find_all('p')
        full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
        print(f"  Successfully scraped {len(full_text)} characters.")
        return full_text
    except Exception as e:
        print(f"  Error scraping article text: {e}")
        return None

def get_ai_insights_from_openrouter(text_content):
    """Sends text to OpenRouter to get a structured summary in Persian."""
    if not text_content or len(text_content) < 200:
        print("  Text too short, skipping AI processing.")
        return None
    print("  Sending text to OpenRouter for AI analysis...")
    prompt = f"""
    You are an expert science communicator translating complex topics for a general Persian-speaking audience. 
    Analyze the following scientific text and provide a response ONLY in a valid JSON object format.
    The entire output must be a single JSON object.
    All string values within the JSON must be in casual, engaging, and modern Persian (Farsi).

    The JSON object must have these exact keys:
    - "summary": A 3-4 sentence summary in a friendly, everyday tone.
    - "highlights": A list of 3-4 key findings as short, bullet-point-style strings.
    - "keywords": A list of 4-5 relevant keywords as strings.
    - "eli5": A single, ultra-simple sentence explaining the core idea as if to a 5-year-old.

    Scientific Text to Analyze:
    ---
    {text_content[:15000]}
    ---
    """
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": YOUR_SITE_URL,
                "X-Title": YOUR_APP_NAME,
            },
            data=json.dumps({
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
            })
        )
        response.raise_for_status()
        ai_response_json = response.json()['choices'][0]['message']['content']
        ai_data = json.loads(ai_response_json)
        print("  Successfully received and parsed AI data from OpenRouter.")
        return ai_data
    except Exception as e:
        print(f"  Error communicating with OpenRouter or parsing its response: {e}")
        return None

# --- Telegram Functions (No changes needed here) ---

def format_telegram_message(title, source_name, source_info, ai_data, link):
    """Creates the final, beautifully formatted message string for Telegram."""
    summary = ai_data.get('summary', 'خلاصه‌ای در دسترس نیست.')
    highlights = ai_data.get('highlights', [])
    keywords = ai_data.get('keywords', [])
    eli5 = ai_data.get('eli5', 'توضیح ساده‌ای در دسترس نیست.')
    title_section = f"🔬 <b>{title}</b>\n\n"
    summary_section = f"📝 <b>خلاصه خودمونی</b>\n{summary}\n\n"
    highlights_section = "✨ <b>نکات کلیدی</b>\n" + "\n".join([f"▪️ {item}" for item in highlights]) + "\n\n" if highlights else ""
    eli5_section = f"🧒 <b>به زبان ساده (ELI5)</b>\n{eli5}\n\n"
    keyword_tags = " ".join([f"#{kw.replace(' ', '_').replace('-', '_')}" for kw in keywords])
    source_tag = source_info['hashtag_en']
    category_tag = '#' + source_info['category_fa'].replace(' ', '_')
    tags_section = f"{source_tag} {category_tag}\n{keyword_tags}"
    link_section = f"🔗 <a href='{link}'>مطالعه مقاله کامل در {source_name}</a>"
    return f"{title_section}{summary_section}{highlights_section}{eli5_section}{link_section}\n\n{tags_section}"

def send_to_telegram(message):
    """Sends a text message to the configured Telegram channel."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHANNEL_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': True}
    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("Successfully sent message to Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

# --- Main Execution Logic (This is where the major changes are) ---

def process_feeds():
    """Main function to run the logic: random, one-per-source, and pre-checked."""
    posted_links = load_posted_links()
    new_links_found = False

    for source_name, source_info in SOURCES.items():
        print(f"--- Checking {source_name} ---")
        try:
            feed = feedparser.parse(source_info['url'])
            
            # Get a list of potential articles (e.g., the 10 most recent)
            potential_entries = feed.entries[:10]
            # Randomly shuffle the list to ensure variety
            random.shuffle(potential_entries)

            # Find the first article in the random list that we haven't posted yet
            for entry in potential_entries:
                if entry.link not in posted_links:
                    print(f"  New random article selected to process: {entry.title}")
                    
                    # --- Start the processing workflow for this one new article ---
                    full_text = scrape_article_text(entry.link)
                    if full_text:
                        ai_data = get_ai_insights_from_openrouter(full_text)
                        if ai_data:
                            message = format_telegram_message(entry.title, source_name, source_info, ai_data, entry.link)
                            send_to_telegram(message)
                            posted_links.add(entry.link)
                            new_links_found = True
                        else:
                            print("  Skipping post due to AI processing failure.")
                    else:
                        print("  Skipping post due to web scraping failure.")
                    
                    # IMPORTANT: Break the loop after processing one article for this source
                    break 
            else: # This 'else' belongs to the 'for' loop
                print(f"  No new articles found in the recent random sample for {source_name}.")

        except Exception as e:
            print(f"Could not process feed for {source_name}. Error: {e}")

    if new_links_found:
        save_posted_links(posted_links)
    else:
        print("No new posts found overall.")

if __name__ == "__main__":
    process_feeds()
