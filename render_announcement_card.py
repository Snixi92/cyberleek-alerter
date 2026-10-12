import os
import datetime
from PIL import Image, ImageDraw, ImageFont

def get_card_font(size, bold=False):
    candidates = []
    if bold:
        candidates = [
            "courbd.ttf", "Courier New Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
            "DejaVuSansMono-Bold.ttf"
        ]
    else:
        candidates = [
            "cour.ttf", "Courier New.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
            "DejaVuSansMono.ttf"
        ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except Exception:
        return ImageFont.load_default()

def render_announcement_card(ann, out_path="announcement_card.png"):
    width = 960
    # Calculer la hauteur dynamique selon le texte
    title = ann.get('title', 'ANNOUNCEMENT').upper()
    body = ann.get('body', '')
    
    tz_fr = datetime.timezone(datetime.timedelta(hours=2))
    ts = ann.get('timestamp', int(datetime.datetime.now().timestamp()))
    dt_str = datetime.datetime.fromtimestamp(ts, tz=tz_fr).strftime("%d oct. %Y, %H:%M")

    # Fonts
    font_head = get_card_font(20, bold=True)
    font_title = get_card_font(25, bold=True)
    font_date = get_card_font(18, bold=False)
    font_body = get_card_font(18, bold=False)
    font_footer = get_card_font(14, bold=False)

    # Word wrapping pour le body
    max_chars = 72
    words = body.split()
    lines = []
    cur_line = ""
    for w in words:
        if len(cur_line) + len(w) + 1 <= max_chars:
            cur_line = f"{cur_line} {w}".strip()
        else:
            if cur_line: lines.append(cur_line)
            cur_line = w
    if cur_line: lines.append(cur_line)

    line_height = 28
    body_height = max(100, len(lines) * line_height)
    height = 240 + body_height

    # Image de base
    img = Image.new("RGBA", (width, height), (0, 5, 13, 255)) # #00050d
    draw = ImageDraw.Draw(img)

    # Grille cybernétique subtile en fond
    grid_color = (0, 30, 80, 50)
    for x in range(0, width, 32):
        draw.line([(x, 0), (x, height)], fill=grid_color)
    for y in range(0, height, 32):
        draw.line([(0, y), (width, y)], fill=grid_color)

    # Scanlines CRT
    scan_color = (0, 0, 0, 45)
    for y in range(0, height, 4):
        draw.line([(0, y), (width, y)], fill=scan_color)

    # Cadre de la carte principale
    card_margin = 24
    card_x1, card_y1 = card_margin, card_margin
    card_x2, card_y2 = width - card_margin, height - card_margin - 30

    # Fond de la carte
    draw.rectangle([card_x1, card_y1, card_x2, card_y2], fill=(0, 22, 100, 230), outline=(0, 50, 153, 255), width=2)
    
    # Glow néon bleu autour de la carte
    draw.rectangle([card_x1-1, card_y1-1, card_x2+1, card_y2+1], outline=(0, 100, 236, 120), width=1)

    # En-tête de la carte (ANNOUNCEMENTS)
    head_height = 44
    draw.rectangle([card_x1, card_y1, card_x2, card_y1 + head_height], fill=(0, 16, 50, 255), outline=(0, 50, 153, 255), width=1)
    
    # Point vert et titre de section
    dot_x, dot_y = card_x1 + 18, card_y1 + 18
    draw.ellipse([dot_x, dot_y, dot_x + 8, dot_y + 8], fill=(96, 195, 58, 255), outline=(150, 255, 100, 255))
    draw.text((dot_x + 18, card_y1 + 11), "ANNOUNCEMENTS", fill=(96, 195, 58, 255), font=font_head)
    
    # Chevron à droite
    draw.text((card_x2 - 30, card_y1 + 10), "▼", fill=(0, 100, 236, 255), font=font_head)

    # Zone du contenu de l'annonce
    content_x = card_x1 + 22
    content_y = card_y1 + head_height + 20

    # Date
    draw.text((content_x, content_y), dt_str, fill=(90, 120, 160, 255), font=font_date)
    content_y += 32

    # Titre de l'annonce en vert/jaune Cyberleek
    draw.text((content_x, content_y), title, fill=(96, 195, 58, 255), font=font_title)
    content_y += 42

    # Ligne de séparation sous le titre
    draw.line([(content_x, content_y), (card_x2 - 22, content_y)], fill=(0, 50, 153, 180), width=1)
    content_y += 18

    # Corps de l'annonce
    for line in lines:
        draw.text((content_x, content_y), line, fill=(160, 176, 200, 255), font=font_body)
        content_y += line_height

    # Footer Cyberleek centré
    footer_text = "CYBERLEEK ON-CHAIN ANNOUNCEMENT • SOLANA DECENTRALIZED PROTOCOL"
    try:
        tw = draw.textlength(footer_text, font=font_footer)
        footer_x = int((width - tw) / 2)
    except Exception:
        footer_x = width // 2 - 260
    # Légère bande de fond sombre pour détacher le footer
    draw.rectangle([footer_x - 12, height - 28, footer_x + tw + 12, height - 8], fill=(0, 5, 13, 230))
    draw.text((footer_x, height - 26), footer_text, fill=(140, 180, 220, 255), font=font_footer)

    img.save(out_path, "PNG")
    print(f"Announcement card generated: {out_path} ({os.path.getsize(out_path)} bytes)")
    return out_path

if __name__ == "__main__":
    test_ann = {
        "title": "CYBERLEEK MILESTONE ROADMAP v2",
        "body": "Every milestone hit means a new GTA 6 leek the next day | Blow past multiple levels and the leeks stack: one per day, in order, until you're caught up | 5M: Mini Tank | 7M: Jumbo jet | 9M: Tank | 11M: Private lap dance | 13M: Police Shootout | 17M: Beach Massacre | 21M: Fighter Jet | 25M: Train vs Train | 30M Full 200+GB playable build. Bigger cap, bigger chaos",
        "timestamp": 1760265240
    }
    render_announcement_card(test_ann, "test_ann_card.png")
