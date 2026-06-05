from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

def compress_image(file_bytes: bytes, content_type: str, max_size_kb: int = 500, quality: int = 85) -> bytes:
    """
    Compresses image bytes using Pillow to fit within a target size.
    Keeps the original format (JPEG, PNG, WebP) or fallback format.
    """
    try:
        image = Image.open(io.BytesIO(file_bytes))
        img_format = image.format
        
        # Determine format if not detected
        if not img_format:
            if "png" in content_type:
                img_format = "PNG"
            elif "webp" in content_type:
                img_format = "WEBP"
            else:
                img_format = "JPEG"

        # Ensure mode compatibility for JPEG saving
        if img_format == "JPEG" and image.mode in ("RGBA", "LA"):
            image = image.convert("RGB")

        # Initial compression attempt
        out_io = io.BytesIO()
        if img_format in ("JPEG", "WEBP"):
            image.save(out_io, format=img_format, quality=quality, optimize=True)
        else:
            # PNG or other lossless/other format
            image.save(out_io, format=img_format, optimize=True)
            
        compressed_bytes = out_io.getvalue()
        
        # If it's still too large, dynamically reduce quality (for lossy formats)
        if len(compressed_bytes) > max_size_kb * 1024 and img_format in ("JPEG", "WEBP"):
            logger.info(f"Image is {len(compressed_bytes)} bytes. Compressing to fit under {max_size_kb}KB.")
            for q in range(quality - 15, 19, -15):
                out_io = io.BytesIO()
                image.save(out_io, format=img_format, quality=q, optimize=True)
                compressed_bytes = out_io.getvalue()
                if len(compressed_bytes) <= max_size_kb * 1024:
                    break
                    
        logger.info(f"Image compressed successfully. Original: {len(file_bytes)} bytes, Compressed: {len(compressed_bytes)} bytes")
        return compressed_bytes
    except Exception as e:
        logger.error(f"Error compressing image: {str(e)}")
        # If compression fails, return original bytes as fallback
        return file_bytes
