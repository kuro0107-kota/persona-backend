import os
from PIL import Image, ImageDraw, ImageFont

def create_sns_assets():
    logo_path = r"c:\Users\kouta\OneDrive\デスクトップ\New business\tinder-proxy-war\frontend\public\logo.png"
    out_icon_path = r"C:\Users\kouta\.gemini\antigravity\brain\35a56520-851a-4aac-9ccf-3feb97238ed7\persona_icon_extracted.png"
    out_header_path = r"C:\Users\kouta\.gemini\antigravity\brain\35a56520-851a-4aac-9ccf-3feb97238ed7\persona_header_pr.png"

    if not os.path.exists(logo_path):
        print(f"Error: Logo not found at {logo_path}")
        return

    # Load original logo
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception as e:
        print(f"Error loading logo: {e}")
        return

    # 1. Create Icon (400x400 square)
    icon_size = 400
    icon = Image.new("RGBA", (icon_size, icon_size), (15, 10, 25, 255)) # Dark deep purple/black background
    
    # Calculate resize ratio to fit logo into 320x320 (leaving margin)
    logo_w, logo_h = logo.size
    ratio = min(320 / logo_w, 320 / logo_h)
    new_w, new_h = int(logo_w * ratio), int(logo_h * ratio)
    logo_resized = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Paste logo centered
    offset_x = (icon_size - new_w) // 2
    offset_y = (icon_size - new_h) // 2
    icon.paste(logo_resized, (offset_x, offset_y), logo_resized)
    
    icon.save(out_icon_path)
    print(f"Icon saved: {out_icon_path}")

    # 2. Create Header (1500x500 banner)
    header_w, header_h = 1500, 500
    header = Image.new("RGBA", (header_w, header_h), (15, 10, 25, 255)) # Dark background
    
    # Draw simple gradient or styling (optional)
    draw = ImageDraw.Draw(header)
    for y in range(header_h):
        r = int(15 + (40 - 15) * (y / header_h))
        g = int(10 + (20 - 10) * (y / header_h))
        b = int(25 + (50 - 25) * (y / header_h))
        draw.line([(0, y), (header_w, y)], fill=(r, g, b, 255))

    # Resize logo for header (height approx 360)
    ratio_h = min(360 / logo_w, 360 / logo_h)
    new_wh_w, new_wh_h = int(logo_w * ratio_h), int(logo_h * ratio_h)
    logo_for_header = logo.resize((new_wh_w, new_wh_h), Image.Resampling.LANCZOS)
    
    # Paste logo on the left
    h_offset_x = 150
    h_offset_y = (header_h - new_wh_h) // 2
    header.paste(logo_for_header, (h_offset_x, h_offset_y), logo_for_header)

    # Try to load a Japanese font (Meiryo or YuGothic)
    font_paths = [
        r"C:\Windows\Fonts\meiryo.ttc",
        r"C:\Windows\Fonts\msgothic.ttc",
        r"C:\Windows\Fonts\yugothr.ttc"
    ]
    
    font_title = None
    font_sub = None
    font_small = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_title = ImageFont.truetype(fp, 64)
            font_sub = ImageFont.truetype(fp, 40)
            font_small = ImageFont.truetype(fp, 32)
            break
            
    if font_title is None:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_small = ImageFont.load_default()
        print("Warning: Japanese font not found. Text might be corrupted.")

    text_x = h_offset_x + new_wh_w + 100
    
    # Draw Texts
    draw.text((text_x, 120), "恋愛を、感情論から科学へ。", font=font_title, fill=(255, 255, 255, 255))
    draw.text((text_x, 220), "AIデジタルツインが100回仮想デートをして", font=font_sub, fill=(220, 200, 255, 255))
    draw.text((text_x, 280), "あなたと相性99%の相手を見極める次世代マッチング", font=font_sub, fill=(220, 200, 255, 255))
    
    # PR Badge / Button-like drawing
    badge_x, badge_y = text_x, 380
    badge_w, badge_h = 500, 60
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], radius=10, fill=(168, 85, 247, 255)) # Purple-500
    draw.text((badge_x + 30, badge_y + 12), "先行ウェイティングリスト 受付中！", font=font_small, fill=(255, 255, 255, 255))

    header.save(out_header_path)
    print(f"Header saved: {out_header_path}")

if __name__ == "__main__":
    create_sns_assets()
