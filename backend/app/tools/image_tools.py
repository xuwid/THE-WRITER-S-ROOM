from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def generate_character_image(
    name: str,
    appearance: str,
    style: str,
    output_dir: str,
    huggingface_token: str = "",
    huggingface_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    prompt = (
        f"Portrait of {name}, {appearance}. Visual style: {style}. "
        "Cinematic, detailed, clean character reference image."
    )
    filename = f"{name.lower().replace(' ', '_')}.png"
    path = out / filename

    if huggingface_token:
        try:
            from huggingface_hub import InferenceClient

            client = InferenceClient(api_key=huggingface_token)
            image = client.text_to_image(
                prompt=prompt,
                model=huggingface_model,
            )
            image.save(path)
            path.with_suffix(".source.txt").write_text("huggingface", encoding="utf-8")
            return str(path)
        except Exception:
            # Fall back to a deterministic local poster so the assignment always produces an image.
            pass

    width, height = 896, 512
    image = Image.new("RGB", (width, height), color=(24, 22, 18))
    draw = ImageDraw.Draw(image)

    # Simple layered panels create a clear visual identity without external generators.
    draw.rectangle((0, 0, width, int(height * 0.28)), fill=(175, 77, 42))
    draw.rectangle((0, int(height * 0.28), width, height), fill=(46, 55, 64))
    draw.rectangle((24, 24, width - 24, height - 24), outline=(236, 214, 168), width=3)

    try:
        title_font = ImageFont.truetype("Arial.ttf", 42)
        body_font = ImageFont.truetype("Arial.ttf", 24)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    draw.text((50, 56), name, fill=(255, 244, 220), font=title_font)
    draw.text((50, 140), f"Style: {style}", fill=(255, 214, 160), font=body_font)

    wrapped = appearance[:180]
    draw.text((50, 190), wrapped, fill=(230, 230, 230), font=body_font)

    image.save(path)
    path.with_suffix(".source.txt").write_text("fallback", encoding="utf-8")
    return str(path)
