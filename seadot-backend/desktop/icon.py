"""Generate an in-memory tray/window icon so the shell has no extra asset files."""

from PIL import Image, ImageDraw


def create_app_icon(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    pad = max(2, size // 16)
    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad),
        radius=size // 4,
        fill=(139, 92, 246, 255),
    )
    arrow_x = size * 0.32
    arrow_y = size * 0.22
    draw.polygon(
        [
            (arrow_x, arrow_y),
            (size * 0.68, size * 0.50),
            (arrow_x, size * 0.78),
        ],
        fill=(255, 255, 255, 255),
    )
    return image
