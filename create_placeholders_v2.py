from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_placeholder(text, output_path, size=(1080, 1920)):
    # Check if exists
    if os.path.exists(output_path):
        print(f"Skipping existing: {output_path}")
        return
        
    img = Image.new('RGB', size, color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        font = ImageFont.load_default()
    
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        if len(' '.join(current_line + [word])) < 25: # Smaller for vertical
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    y_offset = (size[1] - len(lines) * 80) // 2
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            w = bbox[2] - bbox[0]
        except:
            w, _ = draw.textsize(line, font=font)
        x = (size[0] - w) // 2
        draw.text((x, y_offset), line, fill=(200, 200, 200), font=font)
        y_offset += 80
        
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    print(f"Created placeholder: {output_path}")

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
    "Use this power",
    "For example, before a big presentation, visualize yourself speaking with confidence",
    "See the audience nodding",
    "Feel the calm in your chest",
    "Or, if you are an athlete, picture the perfect move before you execute it",
    "Your nervous system is already practicing",
    "Your imagination is a blueprint for your reality",
    "Build it wisely"
]

project_dir = "temp/01_Lemon_Visualization"
# Clear existing images for this project to ensure 9:16 placeholders if needed, 
# or just keep AI ones (they are likely 1:1 or 16:9).
# Actually, the user wants 9:16, my app will now crop/zoom them. 
# So I'll keep AI images and just generate missing placeholders in 9:16.

for i, segment in enumerate(segments):
    create_placeholder(segment, f"{project_dir}/img_{i}.png")
