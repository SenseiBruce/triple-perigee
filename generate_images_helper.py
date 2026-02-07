#!/usr/bin/env python3
"""
Image Generation Helper Script

This script pre-generates all images needed for the video automation workflow.
It parses the input_scripts.json and creates visual prompts for each sentence,
then outputs a list of prompts that can be used with image generation tools.

Usage:
    python generate_images_helper.py

This will create a file 'image_prompts.json' with all the prompts needed.
"""

import json
import re
from pathlib import Path

def generate_visual_prompt(text):
    """Generate a visual prompt from text."""
    clean_text = re.sub(r'[^a-zA-Z0-9\s]', '', text).strip()
    prompt = f"{clean_text}, vertical 9:16 aspect ratio, cinematic lighting, photorealistic, 4k, architectural detail, highly detailed"
    return prompt

def main():
    # Load input scripts
    with open('input_scripts.json', 'r') as f:
        projects = json.load(f)
    
    all_prompts = []
    
    for project in projects:
        project_name = project.get("project_name", "Untitled")
        script_text = project.get("script_text", "")
        
        # Segment script
        sentences = [s.strip() for s in re.split(r'[.!?]', script_text) if s.strip()]
        
        project_prompts = {
            "project_name": project_name,
            "segments": []
        }
        
        for i, sentence in enumerate(sentences):
            prompt = generate_visual_prompt(sentence)
            project_prompts["segments"].append({
                "index": i,
                "sentence": sentence,
                "visual_prompt": prompt,
                "output_path": f"temp/{project_name}/img_{i}.png"
            })
        
        all_prompts.append(project_prompts)
    
    # Save to file
    with open('image_prompts.json', 'w') as f:
        json.dump(all_prompts, f, indent=2)
    
    print("✅ Generated image_prompts.json")
    print(f"📊 Total projects: {len(all_prompts)}")
    print(f"📸 Total images needed: {sum(len(p['segments']) for p in all_prompts)}")
    print("\nNext steps:")
    print("1. Review image_prompts.json")
    print("2. Generate images using your preferred tool (Antigravity, DALL-E, etc.)")
    print("3. Place images in the paths specified in 'output_path'")
    print("4. Run: python main.py")

if __name__ == "__main__":
    main()
