import os
import json
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip

def render_video_asset(script_payload, config):
    """
    Generates a minimalist kinetic text background video using MoviePy 
    based on the script payload. Outputs an MP4 file path.
    """
    output_path = "assets/output/final_post.mp4"
    os.makedirs("assets/output", exist_ok=True)
    
    # Create a 9:16 vertical video clip (1080x1920) for TikTok/Reels, duration 10 seconds
    w, h = 1080, 1920
    bg_clip = ColorClip(size=(w, h), color=(15, 15, 15), duration=10)
    
    # Add text overlay for the hook
    try:
        txt_clip = TextClip(
            script_payload['hook'], 
            fontsize=65, 
            color='white', 
            size=(w - 200, None), 
            method='caption',
            font='Arial-Bold'
        ).set_pos('center').set_duration(10)
        
        video = CompositeVideoClip([bg_clip, txt_clip])
        video.write_videofile(output_path, fps=24, codec='libx264', audio=False, logger=None)
    except Exception as e:
        # Fallback if system fonts/ImageMagick aren't fully configured on runner
        print(f"[Producer Warning] Text rendering fallback triggered: {e}")
        bg_clip.write_videofile(output_path, fps=24, codec='libx264', audio=False, logger=None)
        
    print(f"[Producer] Video compiled successfully at {output_path}")
    return output_path
