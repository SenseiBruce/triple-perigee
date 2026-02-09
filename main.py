import asyncio
import gc
import json
import os
import shutil
import re
from pathlib import Path
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips
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
        prompt = f"{clean_text}, vertical 9:16 aspect ratio, portrait composition, cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
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

    async def process_segment(self, segment_texts, sentence_audio_paths, segment_idx, project_temp_dir, clips_list):
        """
        Processes a group of sentences as a single video segment.
        Generates a visual prompt, image, combines audio, and creates a video clip.
        """
        from PIL import Image, ImageDraw, ImageFont
        
        combined_text = " ".join(segment_texts)
        print(f"  Processing Segment {segment_idx+1}: {combined_text[:70]}...")

        # 1. Generate visual prompt and image
        prompt = self.generate_visual_prompt(combined_text)
        img_path = project_temp_dir / f"img_segment_{segment_idx}.png"
        self.generate_image_asset(prompt, img_path)

        # 2. Combine sentence audios in-memory
        audio_clips_to_combine = [AudioFileClip(str(p)) for p in sentence_audio_paths]
        if not audio_clips_to_combine:
            return

        # Combine all audio clips for this segment
        segment_audio = concatenate_audioclips(audio_clips_to_combine)
        duration = segment_audio.duration

        # 3. Create/Prepare Image Clip
        if not img_path.exists():
            print(f"  [Warning] Image not found for segment {segment_idx}: {img_path}. Skipping segment.")
            return

        img_clip = ImageClip(str(img_path))
        
        # Consistent 9:16 Vertical Framing
        w, h = img_clip.size
        target_w, target_h = VIDEO_SIZE
        scale = max(target_w / w, target_h / h)
        img_clip = img_clip.resize(scale)
        img_clip = img_clip.set_position('center')
        img_clip = img_clip.set_duration(duration)

        # Apply Ken Burns
        img_clip = self.apply_ken_burns(img_clip, duration)
        img_clip = img_clip.set_audio(segment_audio)
        img_clip = img_clip.set_fps(FPS)

        clips_list.append(img_clip)
        
        # We do NOT close the audio clips here as they are nested in segment_audio
        # and needed for the final write. We close them in process_project.
        for p in sentence_audio_paths:
            if p.exists(): os.remove(p)


    async def process_project(self, project):
        project_name = project.get("project_name", "Untitled")
        script_text = project.get("script_text", "")
        
        print(f"\n--- Processing Project: {project_name} ---")
        
        sentences = [s.strip() for s in re.split(r'[.!?]', script_text) if s.strip()]
        
        project_temp_dir = TEMP_DIR / project_name
        project_temp_dir.mkdir(exist_ok=True)
        
        clips = []
        
        # We want segments to be roughly 5-6 seconds.
        # We will iterate through sentences, generate audio for each, and group them.
        
        current_group_text = []
        current_group_audio_paths = []
        current_group_duration = 0
        
        segment_idx = 0
        for i, sentence in enumerate(sentences):
            # Generate temporary audio for just this sentence to check duration
            temp_sentence_audio = project_temp_dir / f"temp_s_{i}.mp3"
            await self.generate_audio_asset(sentence, temp_sentence_audio)
            
            temp_clip = AudioFileClip(str(temp_sentence_audio))
            d = temp_clip.duration
            temp_clip.close()
            
            if current_group_duration + d > 6.0 and current_group_text:
                # Close current group and process as a segment
                await self.process_segment(current_group_text, current_group_audio_paths, segment_idx, project_temp_dir, clips)
                segment_idx += 1
                current_group_text = [sentence]
                current_group_audio_paths = [temp_sentence_audio]
                current_group_duration = d
            else:
                current_group_text.append(sentence)
                current_group_audio_paths.append(temp_sentence_audio)
                current_group_duration += d
                
        # Final group
        if current_group_text:
            await self.process_segment(current_group_text, current_group_audio_paths, segment_idx, project_temp_dir, clips)
        
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
                if clip.audio:
                    clip.audio.close()
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
