import asyncio
import gc
import json
import os
import shutil
import re
from pathlib import Path
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import numpy as np

# --- CONFIGURATION ---
OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")
VOICE = "en-US-ChristopherNeural"
FPS = 24
# Vertical aspect ratio (9:16) for Shorts/TikTok/Reels
VIDEO_SIZE = (1080, 1920)

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

class VideoAutomationApp:
    def __init__(self, input_file):
        self.input_file = input_file
        self.projects = self._load_input()

    def _load_input(self):
        with open(self.input_file, 'r') as f:
            return json.load(f)

    def generate_visual_prompt(self, text):
        """
        Parses text to generate a visual prompt.
        Simple logical extraction for keywords.
        """
        # Simple extraction: remove common stop words and focus on nouns/actions
        # For a more advanced version, we could use an NLP library.
        clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', text).strip()
        # Create a more descriptive prompt for image generation
        prompt = f"{clean_text}, vertical 9:16 aspect ratio, cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
        return prompt

    def generate_image_asset(self, visual_prompt, output_filename):
        """
        [HOOK] Triggers the Antigravity Internal Tool to generate the image.
        Note: This is where the internal tool 'generate_image' is called.
        """
        print(f"  [Internal Tool Hook] Triggering image generation for: {visual_prompt}")
        # In this specific implementation, we assume the Antigravity tool 
        # is coordinated by the agent during the automation process.
        # Developer Note: Replace this with actual API call if running outside this environment.
        pass

    async def generate_audio_asset(self, text, output_filename):
        """
        Generates TTS audio using edge-tts.
        """
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(output_filename)

    def apply_ken_burns(self, clip, duration, zoom_ratio=1.15):
        """
        Applies a smooth Ken Burns (slow zoom) effect to an ImageClip.
        """
        # Function for the zoom effect: 1.0 at t=0, zoom_ratio at t=duration
        def effect(t):
            return 1 + (zoom_ratio - 1) * (t / duration)
        
        return clip.resize(effect)

    async def process_project(self, project):
        project_name = project.get("project_name", "Untitled")
        script_text = project.get("script_text", "")
        
        print(f"\n--- Processing Project: {project_name} ---")
        
        # 1. Segment script into sentences
        sentences = [s.strip() for s in re.split(r'[.!?]', script_text) if s.strip()]
        
        project_temp_dir = TEMP_DIR / project_name
        project_temp_dir.mkdir(exist_ok=True)
        
        clips = []
        
        for i, sentence in enumerate(sentences):
            print(f"  Segment {i+1}/{len(sentences)}: {sentence}")
            
            prompt = self.generate_visual_prompt(sentence)
            img_path = project_temp_dir / f"img_{i}.png"
            audio_path = project_temp_dir / f"audio_{i}.mp3"
            
            # Generate Assets
            self.generate_image_asset(prompt, img_path)
            # IMPORTANT: Wait for image asset if using internal tools asynchronously
            # We assume image generation is instantaneous or handled before this script runs.
            
            await self.generate_audio_asset(sentence, audio_path)
            
            # Load assets and build clip
            # Using ImageClip. To make it work smoothly, we need the audio duration first.
            audio_clip = AudioFileClip(str(audio_path))
            duration = audio_clip.duration
            
            # Check if image exists (since it's an external hook)
            if not img_path.exists():
                print(f"  [Warning] Image {img_path} not found. Using placeholder.")
                # Fallback or Skip (In practical use, the agent ensures this exists)
                continue

            img_clip = ImageClip(str(img_path))
            
            # Resize image to cover the vertical frame (9:16)
            # We want to maintain aspect ratio and fill the screen, so we take the max of width/height ratios
            w, h = img_clip.size
            target_w, target_h = VIDEO_SIZE
            scale = max(target_w / w, target_h / h)
            img_clip = img_clip.resize(scale)
            
            # Center the image
            img_clip = img_clip.set_position('center')
            img_clip = img_clip.set_duration(duration)
            
            # Apply Ken Burns
            img_clip = self.apply_ken_burns(img_clip, duration)
            img_clip = img_clip.set_audio(audio_clip)
            img_clip = img_clip.set_fps(FPS)
            
            clips.append(img_clip)
        
        if clips:
            final_video = concatenate_videoclips(clips, method="compose")
            output_path = OUTPUT_DIR / f"{project_name}.mp4"
            
            # Optimize for M1 (ARM64)
            print(f"  Exporting video to {output_path}...")
            final_video.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                fps=FPS,
                preset="medium",
                threads=4, # M1 performance optimization
                logger="bar"
            )
            
            # Close clips to release memory
            for clip in clips:
                clip.close()
            final_video.close()
        
        # Cleanup temp assets for this project
        shutil.rmtree(project_temp_dir)
        print(f"  Cleaned up temp files for {project_name}.")
        
        # Explicit Garbage Collection
        gc.collect()

    async def run(self):
        for project in self.projects:
            try:
                await self.process_project(project)
            except Exception as e:
                print(f"  [Error] Failed to process project: {e}")
            
        # Final cleanup
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
            print("\nFinal cleanup completed.")

if __name__ == "__main__":
    app = VideoAutomationApp("input_scripts.json")
    asyncio.run(app.run())
