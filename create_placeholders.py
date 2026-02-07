from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_placeholder(text, output_path, size=(1920, 1080)):
    # Create a dark gray background
    img = Image.new('RGB', size, color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, otherwise use default
    try:
        # On macOS, systems fonts are here
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        font = ImageFont.load_default()
    
    # Add text in the center
    # Split text into lines if too long
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        if len(' '.join(current_line + [word])) < 40:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    y_offset = (size[1] - len(lines) * 70) // 2
    for line in lines:
        # Get text bounding box for centering
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (size[0] - w) // 2
        draw.text((x, y_offset), line, fill=(200, 200, 200), font=font)
        y_offset += 70
        
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"Created placeholder: {output_path}")

# Based on segments for 01_Lemon_Visualization
segments = [
    "Close your eyes",
    "Picture a bright yellow lemon in your hand",
    "Feel the bumpy skin",
    "Now, slice it open with a knife",
    "Juice sprays into the air",
    "Bite into the lemon",
    "The sourness explodes in your mouth",
    "Did you salivate?",
    "Your brain cannot tell the difference between reality and imagination",
    "Use this power"
]

project_dir = "temp/01_Lemon_Visualization"
for i, segment in enumerate(segments):
    create_placeholder(segment, f"{project_dir}/img_{i}.png")
