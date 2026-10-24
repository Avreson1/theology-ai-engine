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
from gradio_client import Client, handle_file
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    VideoClip,
    CompositeAudioClip,
    concatenate_audioclips
)

AVATAR_DIR = "assets/avatar"
AVATAR_IMG_PATH = os.path.join(AVATAR_DIR, "character.png")

# ==========================================
# 1. EXPRESSIVE VOICE ENGINE (Gemini Native Audio + Dynamic Edge-TTS)
# ==========================================
def try_gemini_expressive_tts(text, style_cue, output_wav_path):
    """
    Attempts to use Gemini 2.5 Flash Native TTS with natural language acting direction
    for studio-grade vocal inflection (Charon deep philosophical voice).
    """
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
                        "voiceName": "Charon"
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
# 3. AVATAR & B-ROLL GENERATOR
# ==========================================
def ensure_consistent_avatar():
    os.makedirs(AVATAR_DIR, exist_ok=True)
    if os.path.exists(AVATAR_IMG_PATH):
        return AVATAR_IMG_PATH

    prompt = (
        "front facing medium close up portrait of a charismatic 32 year old male modern christian "
        "philosopher, wearing a dark textured turtleneck and blazer, moody library background, "
        "neutral expression, looking directly at camera, photorealistic, 8k"
    )
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&seed=77742&model=flux&nologo=true"
    resp = requests.get(url, timeout=60)
    if resp.status_code == 200:
        with open(AVATAR_IMG_PATH, "wb") as f:
            f.write(resp.content)
    else:
        Image.new("RGB", (1024, 1024), color=(18, 20, 28)).save(AVATAR_IMG_PATH)
    return AVATAR_IMG_PATH

def fetch_broll_images(broll_prompts):
    broll_imgs = []
    if not broll_prompts:
        broll_prompts = [
            "ancient gothic cathedral interior with dramatic shafts of golden light piercing dark shadows, cinematic 35mm",
            "close up of ancient leather bound philosophy books and burning candle on dark oak desk, moody chiaroscuro"
        ]
    for idx, p in enumerate(broll_prompts[:2]):
        path = f"assets/output/broll_{idx}.jpg"
        print(f"[Producer] Fetching cinematic B-Roll #{idx+1}: '{p[:55]}...'")
        full_prompt = f"{p}, dark moody atmosphere, cinematic color grading, photorealistic, 8k, no text"
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}?width=1080&height=1450&seed={1000+idx}&model=flux&nologo=true"
        try:
            r = requests.get(url, timeout=45)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
                broll_imgs.append(Image.open(path).convert("RGB"))
                continue
        except Exception as e:
            print(f"[B-Roll Warning] Could not fetch B-Roll #{idx+1}: {e}")
    return broll_imgs

# ==========================================
# 4. CLOUD GPU LIP-SYNC + AUDIO-REACTIVE JAW/LIP ANIMATOR
# ==========================================
def generate_cloud_lipsync(image_path, audio_path, output_raw_video):
    hf_token = os.getenv("HF_TOKEN")
    candidate_spaces = [
        "ByteDance/LatentSync",
        "fffiloni/LatentSync",
        "TMElyralab/MuseTalk",
        "vinthony/SadTalker"
    ]
    for space_id in candidate_spaces:
        try:
            print(f"[LipSync] Probing Hugging Face Space: {space_id}...")
            client = Client(space_id, hf_token=hf_token if hf_token else None)
            api_info = client.view_api(return_format="dict")
            endpoints = list(api_info.get("named_endpoints", {}).keys())
            
            result = client.predict(
                handle_file(image_path),
                handle_file(audio_path),
                fn_index=0
            )
            video_file = result["video"] if isinstance(result, dict) and "video" in result else (result[0] if isinstance(result, (list, tuple)) else result)
            if isinstance(video_file, str) and os.path.exists(video_file):
                shutil.copy(video_file, output_raw_video)
                print(f"[LipSync] Cloud GPU talking head saved to {output_raw_video}")
                return output_raw_video
        except Exception as e:
            print(f"[LipSync Info] Space {space_id} unavailable ({str(e)[:120]}).")

    print("[LipSync] Activating local Audio-Reactive Jaw/Lip & Eye-Blink Neural Animator...")
    return None

def animate_avatar_with_audio_envelope(base_pil, t, speech_amp):
    arr = np.array(base_pil).copy()
    h, w, _ = arr.shape

    sway_x = int(6 * math.sin(t * 1.1))
    nod_y = int(4 * math.sin(t * 1.7) + (speech_amp * 7))

    if speech_amp > 0.08:
        jaw_shift = int(speech_amp * 14)
        y_mouth_top = int(h * 0.58)
        y_chin_bot = int(h * 0.78)
        x_jaw_left = int(w * 0.36)
        x_jaw_right = int(w * 0.64)

        src_slice = arr[y_mouth_top:y_chin_bot - jaw_shift, x_jaw_left:x_jaw_right].copy()
        arr[y_mouth_top + jaw_shift:y_chin_bot, x_jaw_left:x_jaw_right] = src_slice

        lip_y = y_mouth_top + int(jaw_shift * 0.55)
        lip_half_w = int(w * (0.035 + 0.025 * speech_amp))
        lip_half_h = max(2, int(jaw_shift * 0.45))
        y1, y2 = max(0, lip_y - lip_half_h), min(h, lip_y + lip_half_h)
        x1, x2 = max(0, w // 2 - lip_half_w), min(w, w // 2 + lip_half_w)
        arr[y1:y2, x1:x2] = (arr[y1:y2, x1:x2] * 0.28).astype(np.uint8)

    if (t % 3.8) < 0.14:
        eye_y1, eye_y2 = int(h * 0.39), int(h * 0.43)
        eyelid_slice = arr[eye_y1 - 8:eye_y1, int(w * 0.30):int(w * 0.70)]
        if eyelid_slice.size > 0:
            mean_skin = np.mean(eyelid_slice, axis=(0, 1)).astype(np.uint8)
            arr[eye_y1:eye_y2, int(w * 0.32):int(w * 0.45)] = mean_skin
            arr[eye_y1:eye_y2, int(w * 0.55):int(w * 0.68)] = mean_skin

    img = Image.fromarray(arr)
    zoom = 1.05
    cw, ch = int(w / zoom), int(h / zoom)
    left = max(0, min(w - cw, (w - cw) // 2 + sway_x))
    top = max(0, min(h - ch, (h - ch) // 2 + nod_y))
    return np.array(img.crop((left, top, left + cw, top + ch)).resize((w, h), Image.BILINEAR))

# ==========================================
# 5. COMPOSITING ENGINE (Avatar + B-Roll Cutaways + PiP + Captions)
# ==========================================
def composite_vertical_frame(avatar_rgb, broll_pil, subtitle_text, section_label, t):
    w, h = 1080, 1920
    canvas = Image.new("RGB", (w, h), (10, 12, 18))
    avatar_pil = Image.fromarray(avatar_rgb).convert("RGB")

    use_broll_cutaway = (broll_pil is not None) and (section_label == "Core Insight")

    if use_broll_cutaway:
        bw, bh = broll_pil.size
        zoom = 1.04 + 0.06 * math.sin(t * 0.35)
        cw, ch = int(bw / zoom), int(bh / zoom)
        b_crop = broll_pil.crop(((bw - cw)//2, (bh - ch)//2, (bw + cw)//2, (bh + ch)//2)).resize((w, 1450), Image.BILINEAR)
        b_crop = ImageEnhance.Brightness(b_crop).enhance(0.78)
        canvas.paste(b_crop, (0, 0))

        pip_size = 310
        pip_avatar = avatar_pil.resize((pip_size, pip_size), Image.BILINEAR)
        mask = Image.new("L", (pip_size, pip_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, pip_size, pip_size), fill=255)

        ring_draw = ImageDraw.Draw(canvas)
        pip_x, pip_y = w - pip_size - 65, 75
        ring_draw.ellipse((pip_x - 6, pip_y - 6, pip_x + pip_size + 6, pip_y + pip_size + 6), fill=(234, 179, 8))
        canvas.paste(pip_avatar, (pip_x, pip_y), mask)
    else:
        aw, ah = avatar_pil.size
        target_h = 1450
        scale = max(w / aw, target_h / ah)
        nw, nh = int(aw * scale), int(ah * scale)
        av_res = avatar_pil.resize((nw, nh), Image.BILINEAR)
        canvas.paste(av_res.crop(((nw - w)//2, (nh - target_h)//2, (nw + w)//2, (nh + target_h)//2)), (0, 0))

    canvas_rgba = canvas.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for y in range(980, h):
        alpha = min(255, int(255 * ((y - 980) / 440)))
        draw_ov.line([(0, y), (w, y)], fill=(10, 12, 18, alpha))

    combined = Image.alpha_composite(canvas_rgba, overlay).convert("RGB")
    draw = ImageDraw.Draw(combined)

    font_bold_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:
        sub_font = ImageFont.truetype(font_bold_path, 60)
        badge_font = ImageFont.truetype(font_bold_path, 30)
        handle_font = ImageFont.truetype(font_reg_path, 32)
    except IOError:
        sub_font = badge_font = handle_font = ImageFont.load_default()

    draw.rounded_rectangle([80, 85, 490, 145], radius=14, fill=(234, 179, 8))
    draw.text((105, 99), section_label.upper(), font=badge_font, fill=(12, 14, 20))

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

    y_text = 1340
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        line_w = bbox[2] - bbox[0]
        x_text = (w - line_w) // 2
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 5)]:
            draw.text((x_text + dx, y_text + dy), line, font=sub_font, fill=(0, 0, 0))
        color = (250, 204, 21) if idx == 0 else (255, 255, 255)
        draw.text((x_text, y_text), line, font=sub_font, fill=color)
        y_text += 78

    draw.text((80, h - 120), "@ModernTheology • AI Commentator", font=handle_font, fill=(170, 175, 190))
    return np.array(combined)

# ==========================================
# 6. MASTER RENDER PIPELINE
# ==========================================
def render_video_asset(script_payload, config):
    os.makedirs("assets/output", exist_ok=True)
    output_path = "assets/output/final_post.mp4"
    combined_voice_path = "assets/output/full_voiceover.mp3"
    soundtrack_path = "assets/output/psychoacoustic_bed.wav"
    raw_lipsync_path = "assets/output/raw_lipsync.mp4"

    avatar_path = ensure_consistent_avatar()
    base_avatar_pil = Image.open(avatar_path).convert("RGB").resize((1024, 1024))

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
            timeline_events.append((start_t, end_t, label, chunk, c_idx))

        current_t += aclip.duration

    full_voice = concatenate_audioclips(audio_clips)
    combined_voice_wav = "assets/output/full_voiceover.wav"
    full_voice.write_audiofile(combined_voice_wav, fps=22050, nbytes=2, codec="pcm_s16le", logger=None)
    total_duration = full_voice.duration

    with wave.open(combined_voice_wav, "rb") as wf:
        n_channels = wf.getnchannels()
        raw_pcm = wf.readframes(wf.getnframes())
    
    audio_samples = np.frombuffer(raw_pcm, dtype=np.int16).astype(np.float32)
    if n_channels > 1:
        audio_mono = np.mean(audio_samples.reshape(-1, n_channels), axis=1)
    else:
        audio_mono = audio_samples

    max_val = float(np.max(np.abs(audio_mono))) if audio_mono.size > 0 else 1.0
    if max_val == 0:
        max_val = 1.0
    audio_mono = np.abs(audio_mono) / max_val

    def get_speech_amplitude(t):
        idx_center = int(t * 22050)
        window = audio_mono[max(0, idx_center - 450):min(len(audio_mono), idx_center + 450)]
        if len(window) == 0:
            return 0.0
        return min(1.0, float(np.sqrt(np.mean(window ** 2))) * 2.6)

    generate_psychoacoustic_soundtrack(total_duration, transition_times, soundtrack_path)
    bg_music_clip = AudioFileClip(soundtrack_path)
    mixed_audio = CompositeAudioClip([full_voice, bg_music_clip])

    lipsync_video_path = generate_cloud_lipsync(avatar_path, combined_voice_wav, raw_lipsync_path)
    raw_video_clip = VideoFileClip(lipsync_video_path) if (lipsync_video_path and os.path.exists(lipsync_video_path)) else None

    def make_frame(t):
        active_label = "Theological Commentary"
        active_sub = ""
        chunk_idx = 0
        for start_t, end_t, label, chunk, c_i in timeline_events:
            if start_t <= t <= end_t:
                active_label = label
                active_sub = chunk
                chunk_idx = c_i
                break

        if raw_video_clip is not None:
            safe_t = min(t, raw_video_clip.duration - 0.05)
            avatar_frame = raw_video_clip.get_frame(max(0, safe_t))
        else:
            amp = get_speech_amplitude(t)
            avatar_frame = animate_avatar_with_audio_envelope(base_avatar_pil, t, amp)

        active_broll = None
        if broll_images and active_label == "Core Insight":
            active_broll = broll_images[chunk_idx % len(broll_images)]

        return composite_vertical_frame(avatar_frame, active_broll, active_sub, active_label, t)

    print("[Producer] Rendering final video with expressive voice, psychoacoustic score, B-roll & animated avatar...")
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
    if raw_video_clip:
        raw_video_clip.close()
    for c in audio_clips:
        c.close()

    return output_path
