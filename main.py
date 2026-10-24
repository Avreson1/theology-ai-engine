import os
import sys
import json
import requests

# Ensure the root directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("[*] Initializing imports...")
    from agents.sentinel import scrape_trends
    from agents.architect import generate_theological_script
    from agents.producer import render_video_asset
    print("[*] Imports successful.")
except Exception as e:
    print(f"[!] CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

def run_pipeline():
    try:
        print("[*] Initializing Zero-Touch Autonomous Pipeline...")
        
        with open("config.json", "r") as f:
            config = json.load(f)
            
        print("[1/4] Sentinel: Scraping viral faith & philosophy hooks...")
        trend_data = scrape_trends(config["niche"])
        
        print("[2/4] Architect: Crafting script via Google AI Studio...")
        script_payload = generate_theological_script(trend_data, config)
        print(f"[Architect Output]: {script_payload}")
        
        print("[3/4] Producer: Compiling visual assets and text overlays...")
        video_path = render_video_asset(script_payload, config)
        
        print("[4/4] Dispatcher: Pushing preview card to Telegram...")
        send_telegram_approval(video_path, script_payload)
        print("[+] Pipeline cycle complete. Awaiting human confirmation.")
        
    except Exception as e:
        print(f"[!] PIPELINE ERROR: {e}")
        raise e

def send_telegram_approval(video_path, payload):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("[Dispatcher] Telegram tokens missing. Skipping notification dispatch.")
        return
        
    caption = f"🚨 **New Theological Draft Ready**\n\n**Hook:** {payload.get('hook', '')}\n\n**Body:** {payload.get('body', '')}\n\n**Caption:** {payload.get('caption', '')}"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    with open(video_path, "rb") as video_file:
        response = requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}, files={"video": video_file})
        print(f"[Dispatcher] Telegram API response code: {response.status_code}")

if __name__ == "__main__":
    run_pipeline()
