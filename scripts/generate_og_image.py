"""Generate apps/web/public/og-default.png (1200x630): wordmark + tagline.

No stock imagery, no external assets -- pure Pillow drawing so the file is
reproducible. Run from the repo root: python scripts/generate_og_image.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "apps" / "web" / "public" / "og-default.png"
W, H = 1200, 630
PRIMARY = (0, 102, 204)  # #0066cc
INK = (15, 23, 42)
MUTED = (63, 74, 92)  # matches --muted-foreground 215 22% 32%
BG = (255, 255, 255)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REG_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(candidates, size):
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Left accent bar + thin top rule
    d.rectangle([0, 0, 18, H], fill=PRIMARY)
    d.rectangle([18, 0, W, 6], fill=(214, 226, 240))

    # Shield mark (simple geometry, mirrors the lucide ShieldCheck used in the header)
    sx, sy = 96, 150
    shield = [(sx + 40, sy), (sx + 80, sy + 16), (sx + 80, sy + 52), (sx + 40, sy + 96), (sx, sy + 52), (sx, sy + 16)]
    d.polygon(shield, fill=PRIMARY)
    d.line([(sx + 22, sy + 48), (sx + 36, sy + 62), (sx + 60, sy + 34)], fill=BG, width=9, joint="curve")

    wordmark = _font(FONT_CANDIDATES, 84)
    d.text((sx + 108, sy - 4), "ScopeWise", font=wordmark, fill=INK)

    tagline = _font(FONT_CANDIDATES, 46)
    d.text((sx, 300), "Evidence-based risk reviews.", font=tagline, fill=INK)
    d.text((sx, 360), "Contracts, detections, code.", font=tagline, fill=PRIMARY)

    pillars = _font(FONT_REG_CANDIDATES, 28)
    d.text(
        (sx, 470),
        "SOW & RFP Review   ·   MITRE ATT&CK Coverage   ·   Code Security Review",
        font=pillars,
        fill=MUTED,
    )
    url = _font(FONT_REG_CANDIDATES, 26)
    d.text((sx, 560), "scopewise.assessiq.in", font=url, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
