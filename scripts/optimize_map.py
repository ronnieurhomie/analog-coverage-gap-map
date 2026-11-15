# AI-assisted presentation-asset optimization: OpenAI Codex. Canonical PNG and scientific data unchanged.
"""Generate responsive overview previews from the existing NASA LOLA hillshade; no DEM analysis."""
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
def main():
    source = ROOT / "web/data/lola_84S_hillshade.png"
    with Image.open(source) as image:
        for size in (512, 1024, 1820):
            preview = image if image.size == (size, size) else image.resize((size, size), Image.Resampling.LANCZOS)
            dest = source.with_name(f"lola_84S_hillshade-{size}.webp")
            preview.save(dest, "WEBP", quality=85, method=6)
            print(f"{dest.name}: {dest.stat().st_size:,} bytes")
if __name__ == "__main__":
    main()
