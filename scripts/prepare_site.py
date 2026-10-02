from pathlib import Path
import re
import shutil

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SRC_IMAGES = ROOT / "images"
OUT_IMAGES = DIST / "images" / "optimized"

PHOTO_SPECS = {
    "couple-story.jpg": (1400, 84),
    "couple-01.JPG": (1600, 84),
    "couple-02.jpeg": (1200, 84),
    "couple-03.jpeg": (1200, 84),
    "couple-04.jpeg": (1200, 84),
    "couple-05.jpeg": (1200, 84),
}

ART_SPECS = {
    "Haldi.png": (1440, 92),
    "sangeet.png": (1440, 92),
    "Wedding-1.png": (1440, 92),
    "Wedding-2.png": (1440, 92),
    "Reception.jpeg": (1440, 92),
}


def ignore_source(path: str) -> bool:
    parts = Path(path).parts
    return ".git" in parts or "dist" in parts or ".github" in parts or "scripts" in parts


def optimise_image(filename: str, max_dimension: int, quality: int) -> None:
    source = SRC_IMAGES / filename
    if not source.exists():
        raise FileNotFoundError(source)

    output = OUT_IMAGES / (Path(filename).stem + ".webp")
    with Image.open(source) as image:
        image.load()

        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        if "A" in image.getbands():
            prepared = image.convert("RGBA")
        else:
            prepared = image.convert("RGB")

        prepared.save(
            output,
            format="WEBP",
            quality=quality,
            method=6,
        )

        original_kb = source.stat().st_size / 1024
        optimised_kb = output.stat().st_size / 1024
        print(f"{filename}: {original_kb:.0f} KB -> {optimised_kb:.0f} KB")


def create_preview() -> None:
    """Create a clear, social-friendly JPEG preview from couple-01."""
    source = SRC_IMAGES / "couple-01.JPG"
    output = OUT_IMAGES / "couple-01-preview.jpg"
    target_size = (1280, 640)

    with Image.open(source) as image:
        image = ImageOps.fit(
            image.convert("RGB"),
            target_size,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.42),
        )
        image.save(
            output,
            format="JPEG",
            quality=92,
            optimize=True,
            progressive=True,
        )

    print(f"Preview created: {output}")


def replace_references() -> None:
    replacements = {
        "images/couple-story.jpg": "images/optimized/couple-story.webp",
        "images/couple-01.JPG": "images/optimized/couple-01.webp",
        "images/couple-02.jpeg": "images/optimized/couple-02.webp",
        "images/couple-03.jpeg": "images/optimized/couple-03.webp",
        "images/couple-04.jpeg": "images/optimized/couple-04.webp",
        "images/couple-05.jpeg": "images/optimized/couple-05.webp",
        "images/Haldi.png": "images/optimized/Haldi.webp",
        "images/sangeet.png": "images/optimized/sangeet.webp",
        "images/Wedding-1.png": "images/optimized/Wedding-1.webp",
        "images/Wedding-2.png": "images/optimized/Wedding-2.webp",
        "images/Reception.jpeg": "images/optimized/Reception.webp",
    }

    for path in DIST.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".html", ".css", ".js"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        updated = text
        for old, new in replacements.items():
            updated = updated.replace(old, new)

        if updated != text:
            path.write_text(updated, encoding="utf-8")


def tune_index() -> None:
    path = DIST / "index.html"
    text = path.read_text(encoding="utf-8")

    # The hero is small but is the first visual element, so let the browser
    # request it as early as possible without changing the design.
    if 'rel="preload" as="image"' not in text:
        preload = '  <link rel="preload" as="image" href="images/opening-mandap (1).webp">\n'
        text = text.replace("</head>", preload + "</head>", 1)

    # The story portrait is below the opening viewport on phones, so don't
    # make it compete with the hero for the initial network/decoding budget.
    text = re.sub(
        r'<img src="images/optimized/couple-story\.webp" alt="Shivani and Abhishek — together">',
        '<img src="images/optimized/couple-story.webp" alt="Shivani and Abhishek — together" loading="lazy" decoding="async">',
        text,
        count=1,
    )

    path.write_text(text, encoding="utf-8")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)

    shutil.copytree(
        ROOT,
        DIST,
        ignore=lambda directory, names: {
            name for name in names
            if ignore_source(str(Path(directory, name).relative_to(ROOT)))
        },
    )

    OUT_IMAGES.mkdir(parents=True, exist_ok=True)

    for filename, (max_dimension, quality) in {**PHOTO_SPECS, **ART_SPECS}.items():
        optimise_image(filename, max_dimension, quality)

    create_preview()
    replace_references()
    tune_index()

    print("Optimized site prepared in dist/")


if __name__ == "__main__":
    main()
