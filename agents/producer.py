import os
import io
import wave
import math
import shutil
import asyncio
import base64
import requests
import numpy as np
import edge_tts
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    VideoClip,
    CompositeAudioClip,
    concatenate_audioclips
)

# ==========================================
# 1. EXPRESSIVE VOICE ENGINE (Gemini Native Audio + Dynamic Edge-TTS)
# ==========================================
def try_gemini_expressive_tts(text, style_cue, output_wav_path):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": f"Voice direction: {style_cue}\n\nTranscript: {text}"}]
        }],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": "Charon" # Deep, resonant, philosophical male voice
                    }
                }
            }
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            inline_data = data["candidates"][0]["content"]["parts"][0]["inlineData"]
            pcm_bytes = base64.b64decode(inline_data["data"])
            with wave.open(output_wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(pcm_bytes)
            print("[TTS] Generated studio expressive voice via Gemini Native TTS (Charon).")
            return True
    except Exception as e:
        print(f"[TTS Info] Gemini TTS endpoint skipped ({e}), using Prosody Edge-TTS...")
    return False

async def _generate_dynamic_edge_tts(text, section_type, filename):
    voice = "en-US-BrianMultilingualNeural"
    if section_type == "Theological Hook":
        rate, pitch = "+6%", "-3Hz"
    elif section_type == "Core Insight":
        rate, pitch = "-2%", "-6Hz"
    else:
        rate, pitch = "+8%", "-2Hz"

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(filename)

def generate_voiceover(text, section_type, output_audio_path):
    style_map = {
        "Theological Hook": "Speak with arresting intensity, intriguing and provocative, pausing slightly at ellipses.",
        "Core Insight": "Speak with deep philosophical weight, warm resonance, and intellectual conviction.",
        "Join The Discussion": "Speak directly and engagingly to the listener, challenging them to respond."
    }
    wav_temp = output_audio_path.replace(".mp3", ".wav")
    if try_gemini_expressive_tts(text, style_map.get(section_type, ""), wav_temp):
        aclip = AudioFileClip(wav_temp)
        aclip.write_audiofile(output_audio_path, fps=44100, logger=None)
        aclip.close()
        return

    for attempt in range(3):
        try:
            asyncio.run(_generate_dynamic_edge_tts(text, section_type, output_audio_path))
            print(f"[TTS] Generated dynamic neural voice ({section_type}) via Edge-TTS.")
            return
        except Exception as e:
            print(f"[TTS Retry {attempt+1}/3] Edge-TTS error: {e}")

    from gtts import gTTS
    tts = gTTS(text=text, lang="en", tld="co.uk", slow=False)
    tts.save(output_audio_path)

# ==========================================
# 2. PSYCHOACOUSTIC SOUND DESIGN ENGINE
# ==========================================
def generate_psychoacoustic_soundtrack(total_duration, transition_times, output_wav_path, sr=44100):
    print("[SoundEngine] Synthesizing dark-ambient psychoacoustic score & sub-bass impacts...")
    num_samples = int(total_duration * sr)
    t = np.linspace(0, total_duration, num_samples, endpoint=False)

    lfo = 0.65 + 0.35 * np.sin(2 * np.pi * 0.14 * t)
    drone = (
        0.45 * np.sin(2 * np.pi * 55.0 * t) +
        0.30 * np.sin(2 * np.pi * 82.41 * t + 0.4) +
        0.18 * np.sin(2 * np.pi * 110.0 * t) * lfo +
        0.08 * np.sin(2 * np.pi * 130.81 * t) * (1.0 - lfo * 0.5)
    )

    impacts = np.zeros_like(t)
    for trans_t in [0.0] + transition_times:
        mask = (t >= trans_t) & (t < trans_t + 1.4)
        local_t = t[mask] - trans_t
        freq_sweep = 75.0 * np.exp(-2.2 * local_t) + 28.0
        env = np.exp(-3.0 * local_t) * np.sin(np.pi * np.minimum(local_t / 0.04, 1.0))
        impacts[mask] += 0.85 * env * np.sin(2 * np.pi * freq_sweep * local_t)

    mix = (drone * 0.11) + (impacts * 0.22)
    mix = np.clip(mix, -0.95, 0.95)
    pcm16 = (mix * 32767).astype(np.int16)

    with wave.open(output_wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm16.tobytes())
    return output_wav_path

# ==========================================
# 3. CINEMATIC B-ROLL FETCHER
# ==========================================
def fetch_broll_images(broll_prompts):
    """Downloads stunning cinematic B-Roll images matching the script."""
    broll_imgs = []
    if not broll_prompts:
        broll_prompts = [
            "ancient gothic cathedral interior with dramatic shafts of golden light piercing dark shadows, cinematic 35mm",
            "close up of ancient leather bound philosophy books and burning candle on dark oak desk, moody chiaroscuro",
            "lone figure standing before massive ancient stone archway looking into deep fog, cinematic wide shot"
        ]
    for idx, p in enumerate(broll_prompts[:3]):
        path = f"assets/output/broll_{idx}.jpg"
        print(f"[Producer] Fetching cinematic B-Roll #{idx+1}: '{p[:55]}...'")
        full_prompt = f"{p}, dark moody atmosphere, cinematic color grading, photorealistic, 8k, no text"
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}?width=1080&height=1920&seed={1000+idx}&model=flux&nologo=true"
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                broll_imgs.append(Image.open(path).convert("RGB"))
                continue
        except Exception as e:
            print(f"[B-Roll Warning] Could not fetch B-Roll #{idx+1}: {e}")
            
    # Fallback solid dark moody frame if network fails
    if not broll_imgs:
        fallback = Image.new("RGB", (1080, 1920), color=(14, 16, 22))
        broll_imgs.append(fallback)
    return broll_imgs

# ==========================================
# 4. CINEMATIC COMPOSITING & TYPOGRAPHY ENGINE
# ==========================================
def composite_broll_frame(broll_pil, subtitle_text, section_label, t, segment_duration):
    """
    Renders a stunning 1080x1920 vertical documentary frame:
    - Cinematic slow Ken Burns zoom/pan on the B-roll image
    - Dark professional vignette at bottom for subtitle readability
    - Top section pill badge
    - Kinetic word-by-word subtitles with gold highlighting
    """
    w, h = 1080, 1920
    bw, bh = broll_pil.size
    
    # Smooth Ken Burns slow zoom (from 1.0x to 1.08x over segment duration)
    progress = min(1.0, t / max(segment_duration, 0.1))
    zoom = 1.0 + 0.08 * progress
    cw, ch = int(bw / zoom), int(bh / zoom)
    left = (bw - cw) // 2
    top = (bh - ch) // 2
    
    frame = broll_pil.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BILINEAR)
    frame = ImageEnhance.Brightness(frame).enhance(0.82) # Moody cinematic contrast
    frame_rgba = frame.convert("RGBA")

    # Dark gradient overlay on lower third
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for y in range(950, h):
        alpha = min(245, int(245 * ((y - 950) / 970)))
        draw_ov.line([(0, y), (w, y)], fill=(8, 10, 15, alpha))

    combined = Image.alpha_composite(frame_rgba, overlay).convert("RGB")
    draw = ImageDraw.Draw(combined)

    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        sub_font = ImageFont.truetype(font_bold_path, 62)
        badge_font = ImageFont.truetype(font_bold_path, 30)
        handle_font = ImageFont.truetype(font_reg_path, 32)
    except IOError:
        sub_font = badge_font = handle_font = ImageFont.load_default()

    # Top Section Pill Badge
    draw.rounded_rectangle([80, 90, 480, 150], radius=14, fill=(234, 179, 8))
    draw.text((105, 104), section_label.upper(), font=badge_font, fill=(12, 14, 20))

    # Subtitles in Lower Third
    words = subtitle_text.upper().split()
    lines, cur = [], []
    for word in words:
        test = " ".join(cur + [word])
        bbox = draw.textbbox((0, 0), test, font=sub_font)
        if (bbox[2] - bbox[0]) <= (w - 160):
            cur.append(word)
        else:
            lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))

    y_text = 1320
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        line_w = bbox[2] - bbox[0]
        x_text = (w - line_w) // 2
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
            draw.text((x_text + dx, y_text + dy), line, font=sub_font, fill=(0, 0, 0))
        color = (250, 204, 21) if idx == 0 else (255, 255, 255)
        draw.text((x_text, y_text), line, font=sub_font, fill=color)
        y_text += 80

    # Bottom Watermark
    draw.text((80, h - 130), "@ModernTheology • Philosophical Essays", font=handle_font, fill=(170, 175, 190))
    return np.array(combined)

# ==========================================
# 5. MASTER RENDER PIPELINE
# ==========================================
def render_video_asset(script_payload, config):
    os.makedirs("assets/output", exist_ok=True)
    output_path = "assets/output/final_post.mp4"
    combined_voice_wav = "assets/output/full_voiceover.wav"
    soundtrack_path = "assets/output/psychoacoustic_bed.wav"

    # Fetch cinematic B-Roll images corresponding to script sections
    broll_images = fetch_broll_images(script_payload.get("broll_prompts", []))

    sections = [
        ("Theological Hook", script_payload.get("hook", "")),
        ("Core Insight", script_payload.get("body", "")),
        ("Join The Discussion", script_payload.get("cta", ""))
    ]

    audio_clips = []
    timeline_events = []
    transition_times = []
    current_t = 0.0

    for idx, (label, text) in enumerate(sections):
        if not text.strip():
            continue
        seg_audio_path = f"assets/output/seg_{idx}.mp3"
        generate_voiceover(text, label, seg_audio_path)
        aclip = AudioFileClip(seg_audio_path)
        audio_clips.append(aclip)

        if idx > 0:
            transition_times.append(current_t)

        words = text.split()
        chunks = [" ".join(words[i:i+5]) for i in range(0, len(words), 5)] or [""]
        chunk_dur = aclip.duration / len(chunks)

        for c_idx, chunk in enumerate(chunks):
            start_t = current_t + (c_idx * chunk_dur)
            end_t = start_t + chunk_dur
            timeline_events.append((start_t, end_t, label, chunk, chunk_dur, idx))

        current_t += aclip.duration

    full_voice = concatenate_audioclips(audio_clips)
    full_voice.write_audiofile(combined_voice_wav, fps=22050, nbytes=2, codec="pcm_s16le", logger=None)
    total_duration = full_voice.duration

    # Synthesize psychoacoustic dark-ambient drone + cinematic sub-bass transition impacts
    generate_psychoacoustic_soundtrack(total_duration, transition_times, soundtrack_path)
    bg_music_clip = AudioFileClip(soundtrack_path)
    mixed_audio = CompositeAudioClip([full_voice, bg_music_clip])

    def make_frame(t):
        active_label = "Theological Commentary"
        active_sub = ""
        seg_idx = 0
        seg_dur = 5.0
        
        for start_t, end_t, label, chunk, dur, s_i in timeline_events:
            if start_t <= t <= end_t:
                active_label = label
                active_sub = chunk
                seg_dur = dur
                seg_idx = s_i % len(broll_images)
                break

        active_broll = broll_images[seg_idx] if broll_images else Image.new("RGB", (1080, 1920), (14, 16, 22))
        return composite_broll_frame(active_broll, active_sub, active_label, t, seg_dur)

    print("[Producer] Rendering cinematic B-roll video essay with expressive voice & psychoacoustic score...")
    final_clip = VideoClip(make_frame, duration=total_duration).set_audio(mixed_audio)
    final_clip.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="assets/output/temp-audio.m4a",
        remove_temp=True,
        logger=None
    )

    final_clip.close()
    full_voice.close()
    bg_music_clip.close()
    for c in audio_clips:
        c.close()

    print(f"[Producer] Cinematic B-Roll video successfully compiled at {output_path}")
    return output_path
