import os
import shutil
import asyncio
import requests
import numpy as np
import edge_tts
from gradio_client import Client, handle_file
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    VideoFileClip,
    VideoClip,
    concatenate_audioclips
)

VOICE = "en-US-ChristopherNeural"
AVATAR_DIR = "assets/avatar"
AVATAR_IMG_PATH = os.path.join(AVATAR_DIR, "character.png")

async def _generate_tts(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate="+4%", pitch="-4Hz")
    await communicate.save(filename)

def generate_voiceover(text, output_audio_path):
    asyncio.run(_generate_tts(text, output_audio_path))

def ensure_consistent_avatar():
    """Locks in your character portrait or generates a seed-locked face."""
    os.makedirs(AVATAR_DIR, exist_ok=True)
    if os.path.exists(AVATAR_IMG_PATH):
        print(f"[Producer] Found locked character portrait: {AVATAR_IMG_PATH}")
        return AVATAR_IMG_PATH

    print("[Producer] No custom character.png found. Generating deterministic face (Seed: 77742)...")
    prompt = (
        "front facing medium close up portrait of a charismatic 32 year old male modern christian "
        "philosopher, wearing a dark textured turtleneck and blazer, moody library background, "
        "neutral closed mouth expression, looking directly at camera, photorealistic, 8k"
    )
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1024&height=1024&seed=77742&model=flux&nologo=true"
    
    resp = requests.get(url, timeout=60)
    if resp.status_code == 200:
        with open(AVATAR_IMG_PATH, "wb") as f:
            f.write(resp.content)
        print("[Producer] Master Avatar saved.")
    else:
        img = Image.new("RGB", (1024, 1024), color=(18, 20, 28))
        img.save(AVATAR_IMG_PATH)
    return AVATAR_IMG_PATH

def generate_cloud_lipsync(image_path, audio_path, output_raw_video):
    """
    Attempts to generate a full lip-synced talking head video using free Hugging Face GPU Spaces.
    Includes detailed API introspection so we can debug any Space schema changes immediately.
    """
    hf_token = os.getenv("HF_TOKEN")
    
    # Priority list of public Audio-to-Video LipSync Spaces (SadTalker / Hallo / Sonic / MuseTalk)
    candidate_spaces = [
        {
            "space": "vinthony/SadTalker",
            "type": "sadtalker"
        },
        {
            "space": "fffiloni/SadTalker",
            "type": "sadtalker"
        }
    ]

    for item in candidate_spaces:
        space_id = item["space"]
        try:
            print(f"[LipSync] Connecting to Hugging Face GPU Space: {space_id}...")
            client = Client(space_id, hf_token=hf_token if hf_token else None)
            
            # Print available endpoints in logs for easy troubleshooting
            print(f"[LipSync] Connected to {space_id}. Inspecting API endpoints...")
            api_info = client.view_api(return_format="dict")
            named_endpoints = list(api_info.get("named_endpoints", {}).keys())
            print(f"[LipSync] Available named endpoints on {space_id}: {named_endpoints}")

            # Attempt standard SadTalker prediction call
            print(f"[LipSync] Dispatching image + audio to {space_id} GPU queue (this takes 1-3 mins)...")
            result = client.predict(
                handle_file(image_path),
                handle_file(audio_path),
                "crop",          # preprocess: 'crop' or 'full'
                True,            # still_mode
                False,           # use_enhancer (False is 3x faster and avoids ZeroGPU timeout)
                2,               # batch_size
                256,             # size_of_image
                0,               # pose_style
                fn_index=0
            )
            
            # Extract file path from Gradio response (can be string or dict)
            video_file = result["video"] if isinstance(result, dict) and "video" in result else result
            if isinstance(video_file, str) and os.path.exists(video_file):
                shutil.copy(video_file, output_raw_video)
                print(f"[LipSync] SUCCESS! Talking head video downloaded to {output_raw_video}")
                return output_raw_video

        except Exception as e:
            print(f"[LipSync Warning] Space {space_id} failed or timed out: {e}")

    print("[LipSync Fallback] All public GPU spaces were busy or rate-limited. Falling back to dynamic Ken Burns motion.")
    return None

def composite_vertical_frame(raw_frame_rgb, subtitle_text, section_label):
    """
    Takes a frame from the talking-head video (or static fallback), formats it into a 1080x1920 
    vertical layout, and burns lower-third TikTok captions + header badge.
    """
    w, h = 1080, 1920
    canvas = Image.new("RGB", (w, h), (10, 12, 18))
    
    # Resize talking head to fill upper/center 1080x1350 region cleanly
    avatar_pil = Image.fromarray(raw_frame_rgb).convert("RGB")
    aw, ah = avatar_pil.size
    target_h = 1450
    scale = max(w / aw, target_h / ah)
    new_w, new_h = int(aw * scale), int(ah * scale)
    avatar_resized = avatar_pil.resize((new_w, new_h), Image.BILINEAR)
    
    left = (new_w - w) // 2
    top = (new_h - target_h) // 2
    avatar_cropped = avatar_resized.crop((left, top, left + w, top + target_h))
    canvas.paste(avatar_cropped, (0, 0))

    canvas_rgba = canvas.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # Smooth gradient fade from the bottom of the avatar (Y=1050) into the dark lower-third
    for y in range(1000, h):
        alpha = min(255, int(255 * ((y - 1000) / 420)))
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

    # Top Section Pill Badge
    draw.rounded_rectangle([80, 85, 480, 145], radius=14, fill=(234, 179, 8))
    draw.text((105, 99), section_label.upper(), font=badge_font, fill=(12, 14, 20))

    # Word-wrap 5-word subtitle chunk in lower third (Y=1340)
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

    y_text = 1350
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        line_w = bbox[2] - bbox[0]
        x_text = (w - line_w) // 2
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
            draw.text((x_text + dx, y_text + dy), line, font=sub_font, fill=(0, 0, 0))
        color = (250, 204, 21) if idx == 0 else (255, 255, 255)
        draw.text((x_text, y_text), line, font=sub_font, fill=color)
        y_text += 78

    draw.text((80, h - 120), "@ModernTheology • AI Commentator", font=handle_font, fill=(170, 175, 190))
    return np.array(combined)

def render_video_asset(script_payload, config):
    os.makedirs("assets/output", exist_ok=True)
    output_path = "assets/output/final_post.mp4"
    combined_audio_path = "assets/output/full_voiceover.mp3"
    raw_lipsync_path = "assets/output/raw_lipsync.mp4"

    avatar_path = ensure_consistent_avatar()

    # Step 1: Generate voiceover segments and record timeline boundaries for subtitles
    sections = [
        ("Theological Hook", script_payload.get("hook", "")),
        ("Core Insight", script_payload.get("body", "")),
        ("Join The Discussion", script_payload.get("cta", ""))
    ]

    audio_clips = []
    timeline_events = [] # List of (start_t, end_t, label, chunk_text)
    current_t = 0.0

    for idx, (label, text) in enumerate(sections):
        if not text.strip():
            continue
        seg_audio_path = f"assets/output/seg_{idx}.mp3"
        generate_voiceover(text, seg_audio_path)
        aclip = AudioFileClip(seg_audio_path)
        audio_clips.append(aclip)

        words = text.split()
        chunks = [" ".join(words[i:i+5]) for i in range(0, len(words), 5)] or [""]
        chunk_dur = aclip.duration / len(chunks)

        for c_idx, chunk in enumerate(chunks):
            start_t = current_t + (c_idx * chunk_dur)
            end_t = start_t + chunk_dur
            timeline_events.append((start_t, end_t, label, chunk))

        current_t += aclip.duration

    full_audio = concatenate_audioclips(audio_clips)
    full_audio.write_audiofile(combined_audio_path, fps=44100, logger=None)
    total_duration = full_audio.duration

    # Step 2: Request Cloud GPU Lip-Sync
    lipsync_video_path = generate_cloud_lipsync(avatar_path, combined_audio_path, raw_lipsync_path)

    if lipsync_video_path and os.path.exists(lipsync_video_path):
        raw_video_clip = VideoFileClip(lipsync_video_path)
    else:
        raw_video_clip = None
        fallback_pil = Image.open(avatar_path).convert("RGB")

    # Step 3: Composite talking head + synced lower-third subtitles
    def make_frame(t):
        active_label = "Theological Commentary"
        active_sub = ""
        for start_t, end_t, label, chunk in timeline_events:
            if start_t <= t <= end_t:
                active_label = label
                active_sub = chunk
                break

        if raw_video_clip is not None:
            safe_t = min(t, raw_video_clip.duration - 0.05)
            raw_frame = raw_video_clip.get_frame(max(0, safe_t))
        else:
            # Subtle slow zoom fallback if GPU queue was full
            w0, h0 = fallback_pil.size
            zoom = 1.0 + 0.05 * (t / max(total_duration, 0.1))
            cw, ch = int(w0 / zoom), int(h0 / zoom)
            cropped = fallback_pil.crop(((w0 - cw)//2, (h0 - ch)//2, (w0 + cw)//2, (h0 + ch)//2)).resize((w0, h0), Image.BILINEAR)
            raw_frame = np.array(cropped)

        return composite_vertical_frame(raw_frame, active_sub, active_label)

    print("[Producer] Compositing final 1080x1920 vertical video with audio and captions...")
    final_clip = VideoClip(make_frame, duration=total_duration).set_audio(full_audio)
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
    full_audio.close()
    if raw_video_clip:
        raw_video_clip.close()
    for c in audio_clips:
        c.close()

    return output_path
