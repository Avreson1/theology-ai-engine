import os
import json
import google.generativeai as genai

def generate_theological_script(trend_data, config):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.8-flash")
    
    prompt = f"""
    You are a Modern Theological Commentator on TikTok and Instagram.
    Niche: {config['niche']}
    Persona Tone: {config['tone']}
    
    Based on this trending angle: "{trend_data}", 
    write a short-form video script and visual direction structured strictly as a JSON object:
    1. "hook": First 3 seconds, deeply provocative question or paradox (max 18 words). Use "..." for dramatic pauses.
    2. "body": Core theological/philosophical insight delivered sharply (30-40 words). Use "..." where the speaker should pause for weight.
    3. "cta": Sharp debate question for the comments (max 15 words).
    4. "caption": SEO-optimized caption with Christian philosophy hashtags.
    5. "broll_prompts": A list of 2 cinematic, dark-academia, moody photorealistic image prompts (no text in image) that visually illustrate the "body" argument (e.g., "ancient marble statue of justice crumbling in dark cathedral, chiaroscuro lighting, 35mm film grain").
    
    Return ONLY raw valid JSON with keys: "hook", "body", "cta", "caption", "broll_prompts".
    """
    
    response = model.generate_content(prompt)
    clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)
