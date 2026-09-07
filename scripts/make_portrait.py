import base64
import io
import cv2
import numpy as np
from PIL import Image
from rembg import remove

# Precise light-to-dark density ramp
RAMP = " .:-=+*#%@"
COLS = 84
CHAR_W = 7.74
CHAR_H = 15.2
ROW_ASPECT = 0.49


def generate_ascii_svg(image_path, font_path, output_svg):
    with open(image_path, "rb") as f:
        no_bg_bytes = remove(f.read())

    no_bg = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")

    # Alpha mask to preserve clean outline
    alpha = np.array(no_bg.split()[3])

    # Composite on pure white for accurate luminance calculation
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, mask=no_bg.split()[3])
    gray = np.array(white_bg.convert("L"))

    # Calculate rows maintaining aspect ratio
    h, w = gray.shape
    rows = int(COLS * (h / w) * ROW_ASPECT)

    resized_gray = cv2.resize(gray, (COLS, rows), interpolation=cv2.INTER_AREA)
    resized_alpha = cv2.resize(
        alpha, (COLS, rows), interpolation=cv2.INTER_AREA
    )

    # Enhance edge lines for suit lapels, tie borders, and hair curls
    edges = cv2.Canny(resized_gray, 40, 130)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(6, 6))
    contrast = clahe.apply(resized_gray)

    # Invert so darker features (hair, pupils, tie) use dense characters
    inverted = 255 - contrast

    # Boost edges so tie separation and hair contour stand out
    inverted = np.clip(inverted.astype(np.int16) + (edges * 0.4), 0, 255).astype(
        np.uint8
    )

    # Generate ASCII characters line by line
    ascii_rows = []
    ramp_len = len(RAMP)

    for r in range(rows):
        row_chars = []
        for c in range(COLS):
            # Background area outside person stays completely blank
            if resized_alpha[r, c] < 40:
                row_chars.append(" ")
            else:
                idx = int((inverted[r, c] / 256.0) * ramp_len)
                row_chars.append(RAMP[min(idx, ramp_len - 1)])
        ascii_rows.append("".join(row_chars))

    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")

    svg_w = COLS * CHAR_W
    svg_h = rows * CHAR_H

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">',
        "  <defs>",
        "    <style>",
        "      @font-face {",
        '        font-family: "CustomMono";',
        f"        src: url(data:font/woff2;base64,{font_b64}) format('woff2');",
        "      }",
        "      text {",
        '        font-family: "CustomMono", "Courier New", monospace;',
        "        font-size: 12.8px;",
        "        fill: #24292f;",
        "        white-space: pre;",
        "      }",
        "      @media (prefers-color-scheme: dark) { text { fill: #f0f6fc; } }",
        "    </style>",
    ]

    for i in range(rows):
        start_t = f"{i * 0.05:.2f}s"
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
    print("Sharp ASCII portrait created!")