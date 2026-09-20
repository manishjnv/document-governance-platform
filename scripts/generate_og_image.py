"""Generate the 1200x630 OG images (site default + one per product pillar).

No stock imagery, no external assets -- pure Pillow drawing so the file is
reproducible. Run from the repo root: python scripts/generate_og_image.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "apps" / "web" / "public"

# (file name, line 1 in ink, line 2 in primary, sub-line in muted)
VARIANTS = [
    ("og-default.png", "Evidence-based risk reviews.", "Contracts, detections, code.",
     "SOW & RFP Review   ·   MITRE ATT&CK Coverage   ·   Code Security Review"),
    ("og-sow-review.png", "SOW & RFP Review.", "Evidence for every finding.",
     "Six specialist reviewers + a deterministic rule engine   ·   fix-verification on re-review"),
    ("og-mitre-coverage.png", "MITRE ATT&CK Coverage.", "From rule export to board deck.",
     "Coverage by tactic   ·   ranked gaps   ·   PPTX, XLSX, Navigator layer"),
    ("og-code-security-review.png", "Code Security Review.", "Never sees your client's code.",
     "Scan on your side   ·   upload findings only   ·   register, exploit chains, fix plan"),
]
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


def render(name: str, line1: str, line2: str, subline: str) -> None:
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
    d.text((sx + 108, sy - 4), "ScopeSense", font=wordmark, fill=INK)

    tagline = _font(FONT_CANDIDATES, 46)
    d.text((sx, 300), line1, font=tagline, fill=INK)
    d.text((sx, 360), line2, font=tagline, fill=PRIMARY)

    pillars = _font(FONT_REG_CANDIDATES, 28)
    d.text((sx, 470), subline, font=pillars, fill=MUTED)
    # No host name on purpose: the site is served on two domains during the
    # scopesense.in dual-run (docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md).

    out = OUT_DIR / name
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    print(f"wrote {out} ({W}x{H})")


def main() -> None:
    for variant in VARIANTS:
        render(*variant)


if __name__ == "__main__":
    main()
