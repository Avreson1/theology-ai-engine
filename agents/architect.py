import os
import json
import google.generativeai as genai

def generate_theological_script(trend_data, config):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    prompt = f"""
    You are a Modern Theological Commentator on TikTok and Instagram.
    Niche: {config['niche']}
    Persona Tone: {config['tone']}
    
    Based on this trending angle: "{trend_data}", 
    write a short-form video script structured strictly as follows:
    1. Hook: First 3 seconds, deeply provocative or intellectually engaging question.
    2. Body: Core theological/philosophical insight delivered sharply in under 40 words.
    3. CTA: Engagement driver.
    4. Caption: SEO-optimized caption with relevant Christian philosophy hashtags.
    
    Return the output strictly as a valid JSON object with keys: "hook", "body", "cta", "caption". Do not include markdown code blocks like ```json in the output, just the raw JSON text.
    """
    
    response = model.generate_content(prompt)
    clean_text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)
