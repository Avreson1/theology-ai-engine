import os
import asyncio
import numpy as np
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    ImageClip,
     concatenate_videoclips,
    CompositeAudioClip
)

# Deep, authoritative commentator voice (No API key needed)
VOICE = "en-US-ChristopherNeural"

async def _generate_tts(text, filename):
    communicate = edge_tts.Communicate(text, VOICE, rate="+5%", pitch="-5Hz")
    await communicate.save(filename)

def generate_voiceover(text, output_audio_path):
    """Runs async edge-tts to create an MP3 voiceover file."""
    asyncio.run(_generate_tts(text, output_audio_path))

def create_styled_frame(text, section_label, width=1080, height=1920):
    """
    Uses Pillow to draw a clean, dark-mode theological commentary slide
    without needing ImageMagick.
    """
    # Create dark moody background (Deep charcoal/navy gradient effect)
    img = Image.new("RGB", (width, height), color=(12, 14, 20))
    draw = ImageDraw.Draw(img)

    # Load Ubuntu system DejaVuSans-Bold font (installed via apt in workflow)
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    label_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    try:
        main_font = ImageFont.truetype(font_path, 58)
        label_font = ImageFont.truetype(label_font_path, 34)
    except IOError:
        main_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    # Draw top subtle accent bar & category header
    draw.rectangle([120, 320, 260, 328], fill=(234, 179, 8)) # Gold accent bar
    draw.text((120, 350), section_label.upper(), font=label_font, fill=(234, 179, 8))

    # Word-wrap the main text to fit 1080px width nicely
    words = text.split()
    lines = []
    current_line = []
    max_width = width - 240  # 120px padding on left and right

    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=main_font)
        if (bbox[2] - bbox[0]) <= max_width:
            current_line.append(word)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Calculate vertical centering
    line_height = 82
    total_text_height = len(lines) * line_height
    y_start = (height - total_text_height) // 2

    # Draw each line of text with subtle drop shadow
    for i, line in enumerate(lines):
        y = y_start + (i * line_height)
        # Shadow
        draw.text((124, y + 4), line, font=main_font, fill=(0, 0, 0))
        # Main text (Highlight the first line of the hook in gold, rest in crisp white)
        text_color = (234, 179, 8) if (section_label == "Theological Hook" and i == 0) else (245, 245, 247)
        draw.text((120, y), line, font=main_font, fill=text_color)

    # Draw bottom subtle handle/branding watermark
    draw.text((120, height - 280), "@ModernTheology", font=label_font, fill=(110, 115, 130))

    return np.array(img)

def render_video_asset(script_payload, config):
    """
    1. Synthesizes voiceover for Hook, Body, and CTA.
    2. Builds matching visual slides synced to the exact audio durations.
    3. Combines and exports final MP4 with H.264 video and AAC audio.
    """
    os.makedirs("assets/output", exist_ok=True)
    output_path = "assets/output/final_post.mp4"

    sections = [
        ("Theological Hook", script_payload.get("hook", "")),
        ("Core Insight", script_payload.get("body", "")),
        ("Join The Discussion", script_payload.get("cta", ""))
    ]

    video_clips = []
    temp_audio_files = []

    for idx, (label, text) in enumerate(sections):
        if not text.strip():
            continue
            
        audio_path = f"assets/output/segment_{idx}.mp3"
        temp_audio_files.append(audio_path)
        
        print(f"[Producer] Synthesizing voiceover for segment {idx+1}: {label}...")
        generate_voiceover(text, audio_path)
        
        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration + 0.35  # Small breathing pause between segments
        
        frame_array = create_styled_frame(text, label)
        image_clip = ImageClip(frame_array).set_duration(duration).set_audio(audio_clip)
        video_clips.append(image_clip)

    print("[Producer] Stitching segments and encoding MP4 with audio...")
    final_video = concatenate_videoclips(video_clips, method="compose")
    
    final_video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="assets/output/temp-audio.m4a",
        remove_temp=True,
        logger=None
    )

    # Close clips to release file locks
    final_video.close()
    for clip in video_clips:
        clip.close()

    print(f"[Producer] Full video with voiceover compiled at {output_path}")
    return output_path
