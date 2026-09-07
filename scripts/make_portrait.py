import base64
import io
import cv2
import numpy as np
from PIL import Image
from rembg import remove

# Standard tonal ramp: light to dark
# Space ' ' for background/pure white, dense symbols for dark features
RAMP = " .:-=+*cs#%@"
COLS = 80
CHAR_W = 8.0
CHAR_H = 15.0
ROW_ASPECT = 0.50


def generate_ascii_svg(image_path, font_path, output_svg):
    # 1. Remove background cleanly
    with open(image_path, "rb") as f:
        no_bg_bytes = remove(f.read())

    no_bg = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")

    # Composite onto solid white background
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, mask=no_bg.split()[3])
    img = np.array(white_bg.convert("L"))

    # 2. Resize keeping terminal font aspect ratio
    h, w = img.shape
    rows = int(COLS * (h / w) * ROW_ASPECT)
    resized = cv2.resize(img, (COLS, rows), interpolation=cv2.INTER_AREA)

    # 3. Enhance edge features and normalize lighting
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(resized)

    # Invert tone so dark hair/eyes map to dense characters in RAMP
    inverted = 255 - enhanced

    # 4. Map pixels to characters (mask out original transparent areas)
    mask = cv2.resize(np.array(no_bg.split()[3]), (COLS, rows), interpolation=cv2.INTER_AREA)

    ascii_rows = []
    ramp_len = len(RAMP)
    for r in range(rows):
        row_chars = []
        for c in range(COLS):
            if mask[r, c] < 50:  # Background threshold -> pure space
                row_chars.append(" ")
            else:
                idx = int((inverted[r, c] / 256.0) * ramp_len)
                row_chars.append(RAMP[min(idx, ramp_len - 1)])
        ascii_rows.append("".join(row_chars))

    # 5. Read font subset
    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")

    svg_w = COLS * CHAR_W
    svg_h = rows * CHAR_H

    # 6. Build SVG with locked font layout
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">',
        "  <defs>",
        "    <style>",
        "      @font-face {",
        '        font-family: "CustomMono";',
        f"        src: url(data:font/woff2;base64,{font_b64}) format('woff2');",
        "      }",
        "      text {",
        '        font-family: "CustomMono", "Courier New", Courier, monospace;',
        f"        font-size: 13px;",
        "        letter-spacing: 0px;",
        "        fill: #24292f;",
        "        white-space: pre;",
        "      }",
        "      @media (prefers-color-scheme: dark) { text { fill: #f0f6fc; } }",
        "    </style>",
    ]

    for i in range(rows):
        start_t = f"{i * 0.05:.2f}s"
        svg.append(f'    <clipPath id="c_{i}">')
        svg.append(f'      <rect x="0" y="{i * CHAR_H}" width="0" height="{CHAR_H}">' )
        svg.append(f'        <animate attributeName="width" from="0" to="{svg_w}" dur="0.2s" begin="{start_t}" fill="freeze" />')
        svg.append("      </rect>")
        svg.append("    </clipPath>")

    svg.append("  </defs>")

    for i, row in enumerate(ascii_rows):
        safe_text = row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        y = (i + 1) * CHAR_H - 3
        svg.append(f'  <text x="0" y="{y}" clip-path="url(#c_{i})">{safe_text}</text>')

    svg.append("</svg>")

    with open(output_svg, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


if __name__ == "__main__":
    generate_ascii_svg("photo.jpg", "ramp.woff2", "ascii.svg")
    print("Portrait re-generated with clean mask and aligned spacing!")