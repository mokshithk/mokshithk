import base64
import io
import cv2
import numpy as np
from PIL import Image
from rembg import remove

# Inverted ramp: dark areas map to sparse characters, highlights map to dense characters
RAMP = "@%#sc*+=:-`. "
COLS = 85
CHAR_W = 7.74
CHAR_H = 16.0
ROW_ASPECT = 0.48


def generate_ascii_svg(image_path, font_path, output_svg):
    with open(image_path, "rb") as f:
        no_bg_bytes = remove(f.read())

    no_bg = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")

    # Composite onto solid black to ensure background turns to space (' ')
    black_bg = Image.new("RGBA", no_bg.size, (0, 0, 0, 255))
    black_bg.paste(no_bg, mask=no_bg.split()[3])
    img = np.array(black_bg.convert("L"))

    # Rescale maintaining character aspect ratio
    h, w = img.shape
    rows = int(COLS * (h / w) * ROW_ASPECT)
    resized = cv2.resize(img, (COLS, rows), interpolation=cv2.INTER_AREA)

    # Enhance edge lines and facial features
    filtered = cv2.bilateralFilter(resized, d=5, sigmaColor=40, sigmaSpace=40)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(filtered)

    # Convert pixels to ASCII characters
    ascii_rows = []
    ramp_len = len(RAMP)
    for r in range(rows):
        row_str = "".join(
            RAMP[int((contrast[r, c] / 256.0) * ramp_len)] for c in range(COLS)
        )
        ascii_rows.append(row_str)

    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")

    svg_w = COLS * CHAR_W
    svg_h = rows * CHAR_H

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">',
        "  <defs>",
        "    <style>",
        "      @font-face {",
        '        font-family: "JetBrainsMonoSubset";',
        f"        src: url(data:font/woff2;base64,{font_b64}) format('woff2');",
        "      }",
        "      text {",
        '        font-family: "JetBrainsMonoSubset", monospace;',
        "        font-size: 12.9px;",
        "        fill: #24292f;",
        "        xml:space: preserve;",
        "      }",
        "      @media (prefers-color-scheme: dark) { text { fill: #f0f6fc; } }",
        "    </style>",
    ]

    for i in range(rows):
        start_t = f"{i * 0.07:.2f}s"
        svg.append(f'    <clipPath id="c_{i}">')
        svg.append(
            f'      <rect x="0" y="{i * CHAR_H}" width="0" height="{CHAR_H}">'
        )
        svg.append(
            f'        <animate attributeName="width" from="0" to="{svg_w}" dur="0.25s" begin="{start_t}" fill="freeze" />'
        )
        svg.append("      </rect>")
        svg.append("    </clipPath>")

    svg.append("  </defs>")

    for i, row in enumerate(ascii_rows):
        safe_text = (
            row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        y = (i + 1) * CHAR_H - 3
        svg.append(
            f'  <text x="0" y="{y}" clip-path="url(#c_{i})">{safe_text}</text>'
        )

    svg.append("</svg>")

    with open(output_svg, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


if __name__ == "__main__":
    generate_ascii_svg("photo.jpg", "ramp.woff2", "ascii.svg")
    print("Generated clean ascii.svg successfully!")