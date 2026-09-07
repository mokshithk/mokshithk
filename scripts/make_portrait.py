import base64
import cv2
import numpy as np

# Balanced tonal character ramp mapped from light to dense
RAMP = " .`:-=+*cs#%@"
COLS = 88
CHAR_W = 7.74
CHAR_H = 15.5
ROW_ASPECT = 0.49


def generate_ascii_svg(image_path, font_path, output_svg):
    # 1. Read input photo
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. Compute exact grid dimensions preserving character aspect ratio
    h, w = gray.shape
    rows = int(COLS * (h / w) * ROW_ASPECT)
    resized = cv2.resize(gray, (COLS, rows), interpolation=cv2.INTER_AREA)

    # 3. CLAHE local contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(6, 6))
    contrast = clahe.apply(resized)

    # 4. Multi-directional edge detection (Canny + Sobel)
    # Detects fine hair contours, shirt collar, and tie knot boundaries
    canny = cv2.Canny(resized, 30, 100)

    sobelx = cv2.Sobel(resized, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(resized, cv2.CV_64F, 0, 1, ksize=3)
    sobel_mag = cv2.magnitude(sobelx, sobely)
    sobel_mag = np.uint8(np.clip(sobel_mag, 0, 255))

    # 5. Composite luminance with high-pass edge maps
    combined = contrast.astype(np.float32)
    combined = np.clip(
        combined - (canny * 0.35) - (sobel_mag * 0.25), 0, 255
    ).astype(np.uint8)

    # 6. Map pixels to character ramp and enforce strict uniform line lengths
    ascii_rows = []
    ramp_len = len(RAMP)
    for r in range(rows):
        row_chars = []
        for c in range(COLS):
            val = combined[r, c]
            idx = int(((255 - val) / 256.0) * ramp_len)
            row_chars.append(RAMP[min(ramp_len - 1, max(0, idx))])

        row_str = "".join(row_chars)
        if len(row_str) < COLS:
            row_str = row_str.ljust(COLS, " ")
        ascii_rows.append(row_str)

    # 7. Embed font subset into base64
    with open(font_path, "rb") as f:
        font_b64 = base64.b64encode(f.read()).decode("ascii")

    svg_w = COLS * CHAR_W
    svg_h = rows * CHAR_H

    # 8. Generate SVG with dark/light themes and SMIL typewriter animation
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
        "        font-size: 13px;",
        "        letter-spacing: 0px;",
        "        fill: #24292f;",
        "        white-space: pre;",
        "      }",
        "      @media (prefers-color-scheme: dark) { text { fill: #f0f6fc; } }",
        "    </style>",
    ]

    for i in range(rows):
        start_t = f"{i * 0.04:.2f}s"
        svg.append(f'    <clipPath id="c_{i}">')
        svg.append(
            f'      <rect x="0" y="{i * CHAR_H}" width="0" height="{CHAR_H}">'
        )
        svg.append(
            f'        <animate attributeName="width" from="0" to="{svg_w}" dur="0.2s" begin="{start_t}" fill="freeze" />'
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
    print("ASCII SVG portrait generated successfully!")