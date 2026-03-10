"""Minimal helpers to hide encrypted images inside cover images using LSB.

Why this module exists:
    It provides a small, reusable stego layer for this project, including
    adaptive capacity handling (auto bit-depth selection) and payload format
    compatibility so hide/reveal works reliably across generated images.

Directory layout:
    images/
        encrypted/   # encrypted ROI images (secret payloads)
        covs/        # cover images
        hidden/      # stego outputs
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import struct
from typing import Iterable, Iterator
import xml.etree.ElementTree as ET

from PIL import Image
import numpy as np

from encrypt import IMAGES_ROOT, ensure_directories

HEADER = struct.Struct(">4sBII")
LEGACY_HEADER = struct.Struct(">4sII")
HEADER_MAGIC = b"STEG"

COVERS_DIR = IMAGES_ROOT / "covs"
KEY_DIR = IMAGES_ROOT / "keys"


# Hide an encrypted image inside a cover image.
def hide_image(
    cover_filename: str,
    secret_filename: str,
    *,
    cover_dir: Path,
    secret_dir: Path,
    output_dir: Path,
    output_filename: str | None = None,
    bits_per_channel: int | None = None,
    key: str | None = None,
) -> Path:
    """Hide encrypted image inside a cover and write the stego output."""

    ensure_directories(output_dir, KEY_DIR)
    cover = _load_image(cover_dir / cover_filename).convert("RGB")
    secret = _load_image(secret_dir / secret_filename)

    if key is None:
        key = _load_key_from_store(secret_filename)
    secret_payload = _serialize_image(secret)
    auto_select = bits_per_channel is None

    if auto_select:
        bits_per_channel = _minimum_bits_per_channel(
            len(cover.tobytes()), secret_payload, key
        )
    else:
        _validate_bits_per_channel(bits_per_channel)

    assert bits_per_channel is not None  # narrowed above
    payload = _wrap_payload(secret_payload, key, bits_per_channel)
    required_bits = len(payload) * 8
    capacity = len(cover.tobytes()) * bits_per_channel
    if required_bits > capacity:
        minimum = _minimum_bits_per_channel(
            len(cover.tobytes()), secret_payload, key, allow_none=True
        )
        if minimum is None:
            raise ValueError(
                "Cover image is too small for this secret even at bits_per_channel=8. "
                f"required_bits={required_bits}, available_bits_at_8={len(cover.tobytes()) * 8}. "
                "Use a larger cover image or reduce secret size."
            )
        raise ValueError(
            "Cover image is too small for the requested bit depth. "
            f"required_bits={required_bits}, available_bits={capacity}, "
            f"minimum bits_per_channel={minimum}. "
            "Increase bits_per_channel, use auto selection (None), or choose a larger cover."
        )

    embedded_bytes = bytearray(cover.tobytes())
    _embed_bits(embedded_bytes, payload, bits_per_channel)

    if output_filename:
        output_name = output_filename
    else:
        cover_stem = Path(cover_filename).stem
        output_name = f"{cover_stem}_stego.png"

    target_path = output_dir / output_name
    Image.frombytes("RGB", cover.size, bytes(embedded_bytes)).save(
        target_path, format="PNG"
    )
    return target_path


# Reveal a hidden encrypted image from a stego file.
def reveal_image(
    stego_filename: str,
    *,
    stego_dir: Path,
    output_dir: Path,
    recovered_filename: str | None = None,
    bits_per_channel: int | None = None,
) -> Path:
    """Extract the hidden encrypted image and save to the reveal dir."""

    ensure_directories(output_dir)
    stego = _load_image(stego_dir / stego_filename).convert("RGB")

    raw_bytes = stego.tobytes()
    payload_bytes, key_text = _extract_payload(raw_bytes, bits_per_channel)
    secret_path = output_dir / (recovered_filename or stego_filename)
    with Image.open(io.BytesIO(payload_bytes)) as hidden:
        hidden.load()
        hidden.save(secret_path)
    _write_key_record(secret_path.name, key_text)
    return secret_path


# Convenience wrapper to extract from a stego cover file.
def extract_hidden_image(
    cover_filename: str,
    *,
    stego_dir: Path,
    output_dir: Path,
    recovered_filename: str | None = None,
    bits_per_channel: int = 1,
) -> Path:
    """Convenience wrapper to extract from a stego cover image."""

    return reveal_image(
        cover_filename,
        recovered_filename=recovered_filename,
        bits_per_channel=bits_per_channel,
        stego_dir=stego_dir,
        output_dir=output_dir,
    )


# Serialize an image as PNG bytes.
def _serialize_image(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# Prefix payload with a header for validation and length.
def _wrap_payload(payload: bytes, key: str, bits_per_channel: int) -> bytes:
    key_bytes = key.encode("utf-8")
    return (
        HEADER.pack(HEADER_MAGIC, bits_per_channel, len(payload), len(key_bytes))
        + payload
        + key_bytes
    )


# Load an image from disk into memory.
def _load_image(path: Path) -> Image.Image:
    with Image.open(path) as img:
        img.load()
        return img.copy()


def _key_record_path(image_name: str) -> Path:
    safe_name = Path(image_name).name
    return KEY_DIR / f"{safe_name}.xml"


def _write_key_record(image_name: str, key: str) -> Path:
    ensure_directories(KEY_DIR)
    root = ET.Element("encryption")
    ET.SubElement(root, "image").text = image_name
    ET.SubElement(root, "key").text = key
    tree = ET.ElementTree(root)
    path = _key_record_path(image_name)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


def _load_key_from_store(image_name: str) -> str:
    path = _key_record_path(image_name)
    if not path.exists():
        raise ValueError(
            f"No stored key found for {image_name}. Provide key explicitly."
        )

    tree = ET.parse(path)
    recorded_name = tree.findtext("image") or image_name
    if Path(recorded_name).name != Path(image_name).name:
        raise ValueError("Stored key record does not match the requested image.")
    key_text = tree.findtext("key")
    if not key_text:
        raise ValueError("Stored key file is missing a <key> entry.")
    return key_text.strip()


def _validate_bits_per_channel(bits_per_channel: int) -> None:
    if not isinstance(bits_per_channel, int) or not (1 <= bits_per_channel <= 8):
        raise ValueError("bits_per_channel must be an integer in the range 1..8.")


def _minimum_bits_per_channel(
    carrier_byte_length: int, payload: bytes, key: str, *, allow_none: bool = False
) -> int | None:
    key_bytes = key.encode("utf-8")
    base_bytes = HEADER.size + len(payload) + len(key_bytes)
    required_bits = base_bytes * 8
    if required_bits > carrier_byte_length * 8:
        if allow_none:
            return None
        raise ValueError(
            "Cover image is too small for this secret even at bits_per_channel=8. "
            f"required_bits={required_bits}, available_bits_at_8={carrier_byte_length * 8}. "
            "Use a larger cover image or reduce secret size."
        )
    return max(1, math.ceil(required_bits / carrier_byte_length))


def _extract_payload(raw_bytes: bytes, bits_per_channel: int | None) -> tuple[bytes, str]:
    if bits_per_channel is not None:
        _validate_bits_per_channel(bits_per_channel)
        parsed = _try_extract_payload(raw_bytes, bits_per_channel)
        if parsed is None:
            raise ValueError(
                f"Image does not contain a valid LSB payload at bits_per_channel={bits_per_channel}."
            )
        return parsed

    for candidate in range(1, 9):
        parsed = _try_extract_payload(raw_bytes, candidate)
        if parsed is not None:
            return parsed
    raise ValueError("Image does not contain a valid LSB payload at bit depths 1..8.")


def _try_extract_payload(raw_bytes: bytes, bits_per_channel: int) -> tuple[bytes, str] | None:
    parsed = _parse_versioned_payload(raw_bytes, bits_per_channel)
    if parsed is not None:
        return parsed
    return _parse_legacy_payload(raw_bytes, bits_per_channel)


def _parse_versioned_payload(
    raw_bytes: bytes, bits_per_channel: int
) -> tuple[bytes, str] | None:
    bit_capacity = len(raw_bytes) * bits_per_channel
    if bit_capacity < HEADER.size * 8:
        return None

    bit_source = _lsb_stream(raw_bytes, bits_per_channel)
    header_bytes = _consume_bits(bit_source, HEADER.size)
    magic, embedded_bpc, payload_length, key_length = HEADER.unpack(header_bytes)
    if magic != HEADER_MAGIC or embedded_bpc != bits_per_channel:
        return None
    total_bits = (HEADER.size + payload_length + key_length) * 8
    if total_bits > bit_capacity:
        return None

    payload_bytes = _consume_bits(bit_source, payload_length)
    key_bytes = _consume_bits(bit_source, key_length)
    try:
        key_text = key_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return payload_bytes, key_text


def _parse_legacy_payload(raw_bytes: bytes, bits_per_channel: int) -> tuple[bytes, str] | None:
    bit_capacity = len(raw_bytes) * bits_per_channel
    if bit_capacity < LEGACY_HEADER.size * 8:
        return None

    bit_source = _lsb_stream(raw_bytes, bits_per_channel)
    header_bytes = _consume_bits(bit_source, LEGACY_HEADER.size)
    magic, payload_length, key_length = LEGACY_HEADER.unpack(header_bytes)
    if magic != HEADER_MAGIC:
        return None

    total_bits = (LEGACY_HEADER.size + payload_length + key_length) * 8
    if total_bits > bit_capacity:
        return None

    payload_bytes = _consume_bits(bit_source, payload_length)
    key_bytes = _consume_bits(bit_source, key_length)
    try:
        key_text = key_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return payload_bytes, key_text


# Embed payload bits into the carrier's LSBs.
def _embed_bits(carrier: bytearray, payload: bytes, bits_per_channel: int) -> None:
    mask = (1 << bits_per_channel) - 1
    bits = list(_byte_to_bits(payload))
    cursor = 0
    total = len(bits)

    for index, value in enumerate(carrier):
        chunk = 0
        written = 0
        while written < bits_per_channel and cursor < total:
            chunk = (chunk << 1) | bits[cursor]
            cursor += 1
            written += 1
        if written and written < bits_per_channel:
            chunk <<= bits_per_channel - written
        carrier[index] = (value & ~mask) | chunk
        if cursor >= total:
            return
    raise ValueError("Carrier does not have enough capacity for the payload.")


# Iterate over LSBs in a byte stream.
def _lsb_stream(data: bytes, bits_per_channel: int) -> Iterator[int]:
    mask = (1 << bits_per_channel) - 1
    for byte in data:
        chunk = byte & mask
        for shift in reversed(range(bits_per_channel)):
            yield (chunk >> shift) & 1


# Consume bits from the iterator to rebuild bytes.
def _consume_bits(bit_iter: Iterator[int], length: int) -> bytes:
    collected = bytearray()
    byte = 0
    for index in range(length * 8):
        try:
            bit = next(bit_iter)
        except StopIteration as exc:
            raise ValueError("Not enough bits available in the carrier.") from exc
        byte = (byte << 1) | bit
        if (index + 1) % 8 == 0:
            collected.append(byte)
            byte = 0
    return bytes(collected)


# Yield bits from each byte, MSB to LSB.
def _byte_to_bits(data: Iterable[int]) -> Iterator[int]:
    for byte in data:
        for shift in range(7, -1, -1):
            yield (byte >> shift) & 1


# Phase 1: New Image-in-Image Functions (2-bit LSB)
def hide_secret_image(cover_path: str, secret_path: str, output_path: str) -> str:
    """
    Hides a Secret Image inside a Cover Image using 2-bit LSB.
    """
    cover = Image.open(cover_path).convert("RGB")
    secret = Image.open(secret_path).convert("RGB")
    
    # 1. Resize cover to match secret if necessary
    # (We MUST preserve the secret's original dimensions because 
    # the ROI decryption relies on exact coordinate mapping)
    if cover.size != secret.size:
        cover = cover.resize(secret.size)
        
    cover_data = np.array(cover)
    secret_data = np.array(secret)

    # 2. Shift secret bits to become the LSBs (keeping only the most significant 2 bits)
    # We take the top 2 bits of the secret and prepare to put them in the bottom 2 of the cover
    secret_bits = (secret_data >> 6) 

    # 3. Clear the last 2 bits of the cover and inject secret bits
    # 252 is 11111100 in binary
    cleared_cover = cover_data & 252 
    stego_data = cleared_cover | secret_bits

    # 4. Save the result
    stego_img = Image.fromarray(stego_data)
    stego_img.save(output_path)
    return output_path

def reveal_secret_image(stego_path: str, output_path: str) -> str:
    """
    Extracts the hidden image from the 2-bit LSBs.
    """
    stego = Image.open(stego_path).convert("RGB")
    stego_data = np.array(stego)

    # 1. Extract the last 2 bits
    # 3 is 00000011 in binary
    extracted_bits = stego_data & 3

    # 2. Shift them back to being the Most Significant Bits
    revealed_data = extracted_bits << 6

    # 3. Save revealed image
    revealed_img = Image.fromarray(revealed_data)
    revealed_img.save(output_path)
    return output_path


__all__ = [
    "hide_image",
    "reveal_image",
    "extract_hidden_image",
    "hide_secret_image",
    "reveal_secret_image",
    "COVERS_DIR",
    "KEY_DIR",
]
