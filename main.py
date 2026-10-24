import os
import json
import requests
from agents.sentinel import scrape_trends
from agents.architect import generate_theological_script
from agents.producer import render_video_asset

def run_pipeline():
    print("[*] Initializing Zero-Touch Autonomous Pipeline...")
    
    with open("config.json", "r") as f:
        config = json.load(f)
        
    print("[1/4] Sentinel: Scraping viral faith & philosophy hooks...")
    trend_data = scrape_trends(config["niche"])
    
    print("[2/4] Architect: Crafting script via Google AI Studio...")
    script_payload = generate_theological_script(trend_data, config)
    
    print("[3/4] Producer: Compiling visual assets and text overlays...")
    video_path = render_video_asset(script_payload, config)
    
    print("[4/4] Dispatcher: Pushing preview card to Telegram...")
    send_telegram_approval(video_path, script_payload)
    print("[+] Pipeline cycle complete. Awaiting human confirmation.")

def send_telegram_approval(video_path, payload):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("[Dispatcher] Telegram tokens missing. Skipping notification dispatch.")
        return
        
    caption = f"🚨 **New Theological Draft Ready**\n\n**Hook:** {payload['hook']}\n\n**Body:** {payload['body']}\n\n**Caption:** {payload['caption']}"
    
    url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){bot_token}/sendVideo"
    with open(video_path, "rb") as video_file:
        requests.post(url, data={"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}, files={"video": video_file})

if __name__ == "__main__":
    run_pipeline()
