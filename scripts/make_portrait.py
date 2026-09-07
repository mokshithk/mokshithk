import base64
import io
import cv2
import numpy as np
from PIL import Image
from rembg import remove

RAMP = " .`:-=+*cs#%@"
COLS = 90
CHAR_W = 7.74
CHAR_H = 16.0
ROW_ASPECT = 0.48


def generate_ascii_svg(image_path, font_path, output_svg):
    # 1. Remove background
    with open(image_path, "rb") as f:
        no_bg_bytes = remove(f.read())
    
    # Read returned image bytes directly
    no_bg = Image.open(io.BytesIO(no_bg_bytes)).convert("RGBA")

    # Composite onto solid white
    white_bg = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
    white_bg.paste(no_bg, mask=no_bg.split()[3])
    img = np.array(white_bg.convert("L"))

    # 2. Rescale maintaining character aspect ratio
    h, w = img.shape
    rows = int(COLS * (h / w) * ROW_ASPECT)
    resized = cv2.resize(img, (COLS, rows), interpolation=cv2.INTER_AREA)

    # 3. Bilateral filter & CLAHE contrast
    filtered = cv2.bilateralFilter(resized, d=7, sigmaColor=50, sigmaSpace=50)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    contrast = clahe.apply(filtered)

    # 4. Apply darkening curve to bring out facial lines
    curve = np.power(contrast / 255.0, 1.7) * 255.0
    curve = np.clip(curve, 0, 255).astype(np.uint8)

    # 5. Convert pixels to character ramp
    ascii_rows = []
    ramp_len = len(RAMP)
    for r in range(rows):
        row_str = "".join(
            RAMP[int((curve[r, c] / 256.0) * ramp_len)] for c in range(COLS)
        )
        ascii_rows.append(row_str)

    # 6. Read font into base64
    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")

    svg_w = COLS * CHAR_W
    svg_h = rows * CHAR_H

    # 7. Construct SVG with SMIL typing animations
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
        start_t = f"{i * 0.09:.2f}s"
        svg.append(f'    <clipPath id="c_{i}">')
        svg.append(
            f'      <rect x="0" y="{i * CHAR_H}" width="0" height="{CHAR_H}">'
        )
        svg.append(
            f'        <animate attributeName="width" from="0" to="{svg_w}" dur="0.3s" begin="{start_t}" fill="freeze" />'
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
    print("Generated ascii.svg successfully!")