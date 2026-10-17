"""Preview English standalone package PNGs; --write creates isolated copies.

Only measured logo bands are replaced. The clean Wizardry wordmark and fog come
from the original title texture, with English rendered using the supplied font.
Portrait images are retained verbatim. Original files are never overwritten.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont
from enc_archive import unpack

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "work/source/NPJB00162"
DEFAULT_MANIFEST = ROOT / "work/translation/en/graphics/package.en.json"
DEFAULT_OUTPUT = ROOT / "work/output/metadata/package_png"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def box(rect):
    x, y, w, h = rect
    return x, y, x + w, y + h


def text(layer, rect, value, font_path, size, fill, outline=None):
    x, y, w, h = rect
    draw = ImageDraw.Draw(layer)
    for px in range(size, 9, -1):
        font = ImageFont.truetype(str(font_path), px)
        stroke = 1 if outline else 0
        b = draw.textbbox((0, 0), value, font=font, stroke_width=stroke)
        if b[2] - b[0] <= w - 6 and b[3] - b[1] <= h - 4:
            draw.text((x + (w - b[2] + b[0]) // 2 - b[0],
                       y + (h - b[3] + b[1]) // 2 - b[1]), value,
                      font=font, fill=fill, stroke_width=stroke,
                      stroke_fill=outline or fill)
            return px
    raise ValueError("Text does not fit: " + value)


def generate(source=DEFAULT_SOURCE, manifest_path=DEFAULT_MANIFEST):
    source = Path(source)
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    title_data = (source / "USRDIR/data/texture/title.enc").read_bytes()
    title = Image.open(io.BytesIO(unpack(title_data)[3])).convert("RGBA")
    upper = title.crop((0, 0, 1280, 220))
    wordmark = upper.crop(upper.getbbox())
    fog = title.crop((350, 330, 950, 405))
    font_path = source / "USRDIR/FOT-UtrilloPro-DB.otf"
    files, records = {}, []
    for asset in manifest["assets"]:
        relative = asset["package_path"]
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError("Unsafe package path")
        original = (source / relative).read_bytes()
        if sha(original) != asset["sha256"]:
            raise ValueError("Source image hash changed: " + relative)
        if not asset["regions"]:
            continue
        image = Image.open(io.BytesIO(original)).convert("RGBA")
        if image.size != (asset["width"], asset["height"]):
            raise ValueError("Unexpected image dimensions")
        rect = asset["edit_rect"]
        if not (0 <= rect[0] < rect[0] + rect[2] <= image.width and
                0 <= rect[1] < rect[1] + rect[3] <= image.height):
            raise ValueError("Edit rectangle outside image")
        rendered = image.copy()
        rendered.paste((255, 255, 255, 0), box(rect))
        layer = Image.new("RGBA", image.size)
        for part, target in ((fog, asset["fog_rect"]), (wordmark, asset["wordmark_rect"])):
            x, y, w, h = target
            layer.alpha_composite(part.resize((w, h), Image.Resampling.LANCZOS), (x, y))
        regions = {r["id"]: r for r in asset["regions"]}
        px = text(layer, asset["english_rect"], regions["subtitle"]["en"], font_path,
                  asset["font_size"], (145, 168, 255, 255), (235, 240, 255, 255))
        if "trial" in regions:
            d = ImageDraw.Draw(layer)
            r = asset["demo_rect"]
            b = box(r)
            d.rectangle((b[0], b[1], b[2] - 1, b[3] - 1), fill=(0, 0, 0, 255), outline=(230, 191, 60, 255), width=1)
            text(layer, r, regions["trial"]["en"], font_path, r[3] - 6, (255, 217, 90, 255))
        if asset.get('footer'):
            text(layer,asset['footer_rect'],asset['footer'],font_path,18,(255,217,90,255))
        # Clip every replacement to its declared rectangle, including resampling.
        rendered.alpha_composite(layer.crop(box(rect)), (rect[0], rect[1]))
        diff = ImageChops.difference(image, rendered)
        diff.paste((0, 0, 0, 0), box(rect))
        if any(channel.getbbox() for channel in diff.split()):
            raise ValueError("Pixels outside edit rectangle changed: " + relative)
        buffer = io.BytesIO()
        rendered.save(buffer, format="PNG", compress_level=9)
        encoded = buffer.getvalue()
        decoded = Image.open(io.BytesIO(encoded)).convert("RGBA")
        if decoded.tobytes() != rendered.tobytes():
            raise ValueError("PNG roundtrip changed pixels")
        files[relative] = encoded
        records.append(dict(path=relative, size=list(image.size), edit_rect=rect,
                            before_sha256=sha(original), after_sha256=sha(encoded),
                            subtitle_font_size=px, outside_pixels_identical=True,
                            png_roundtrip_exact=True, status="review",
                            note="Proposed transparent logo-band reconstruction; verify native XMB layout."))
    report = dict(format="package-graphics-v1", changed_assets=len(files),
                  untouched_portrait_assets=3, source_title_sha256=sha(title_data),
                  font_sha256=sha(font_path.read_bytes()), assets=records)
    return files, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    files, report = generate()
    output = args.output.resolve()
    allowed = (ROOT / "work/output/metadata").resolve()
    if allowed not in output.parents:
        parser.error("PNG output must be a subdirectory of work/output/metadata")
    if args.write:
        if output.exists():
            parser.error("Refusing to overwrite existing output: " + str(output))
        output.mkdir(parents=True, exist_ok=False)
        files["verification.en.json"] = (json.dumps(report, indent=2) + "\n").encode()
        for relative, data in files.items():
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
    print(json.dumps(dict(written=args.write, output=str(output), **report), indent=2))


if __name__ == "__main__":
    main()
