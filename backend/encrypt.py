"""Simple selective image encryption helpers tied to the local images folder.

The goal is intentionally small in scope:

* read an image from ``images/input``,
* encrypt only the requested coordinates,
* save the encrypted image to ``images/encrypted``,
* optionally decrypt the same pixels back into ``images/decrypted``.
Nothing prevents calling the helpers with explicit paths, but keeping a default
directory structure removes the need for extra command-line wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import secrets
from typing import Iterable, Iterator, Sequence, Set, Tuple
import xml.etree.ElementTree as ET
import io

from PIL import Image, ImageFilter

try:
    from Crypto.Cipher import AES
    from Crypto.Util import Counter
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "PyCryptodome is required (pip install pycryptodome) to use AES encryption."
    ) from exc

Coordinate = Tuple[int, int]
CoordinateList = Sequence[Coordinate]

FIXED_ROI: Tuple[Coordinate, Coordinate] = ((50, 50), (150, 150))

IMAGES_ROOT = Path("images")
KEY_DIR = IMAGES_ROOT / "keys"


@dataclass(frozen=True)
class EncryptionResult:
    image: Image.Image
    coordinates: CoordinateList
    output_path: Path
    key: str
    metadata_path: Path | None = None
    key_record_path: Path | None = None


# Encrypt and blur ROI, saving metadata and key.
def encrypt_image(
    filename: str,
    key: str | None = None,
    *,
    input_dir: Path,
    output_dir: Path,
    coordinates: Iterable[Coordinate] | None = None,
    boxes: Iterable[Tuple[Coordinate, Coordinate]] | None = None,
) -> EncryptionResult:
    """Blur the ROI (defaults to a fixed region) and store the original pixels securely."""

    ensure_directories(output_dir, KEY_DIR)
    source_path = input_dir / filename
    target_path = output_dir / filename
    used_key = key or generate_key()
    roi_coords = _merge_roi_coordinates(coordinates, boxes, source_path.name)
    return _encrypt_flow(source_path, target_path, roi_coords, used_key)


# Restore ROI from encrypted metadata.
def decrypt_image(
    filename: str,
    key: str | None = None,
    *,
    input_dir: Path,
    output_dir: Path,
    coordinates: Iterable[Coordinate] | None = None,
    boxes: Iterable[Tuple[Coordinate, Coordinate]] | None = None,
) -> EncryptionResult:
    """Restore the blurred ROI using the encrypted metadata captured during encryption."""

    if key is None:
        key = _load_key_from_store(Path(filename).name)

    ensure_directories(output_dir)
    source_path = input_dir / filename
    target_path = output_dir / filename
    roi_coords = _merge_roi_coordinates(coordinates, boxes, source_path.name)
    return _decrypt_flow(source_path, target_path, roi_coords, key)


# Expand a rectangular ROI into pixel coordinates.
def box_coordinates(top_left: Coordinate, bottom_right: Coordinate) -> Iterator[Coordinate]:
    """Yield every coordinate inside an inclusive axis-aligned box."""

    (x0, y0), (x1, y1) = top_left, bottom_right
    if x0 > x1 or y0 > y1:
        raise ValueError("Top-left must be above and to the left of bottom-right.")

    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            yield (x, y)


# Create directories if they do not exist.
def ensure_directories(*directories: Path) -> None:
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Build the XML key record path for an image name.
def _key_record_path(image_name: str) -> Path:
    safe_name = Path(image_name).name
    return KEY_DIR / f"{safe_name}.xml"


# Persist the encryption key to an XML file.
def _write_key_record(image_name: str, key: str) -> Path:
    ensure_directories(KEY_DIR)
    root = ET.Element("encryption")
    ET.SubElement(root, "image").text = image_name
    ET.SubElement(root, "key").text = key
    tree = ET.ElementTree(root)
    path = _key_record_path(image_name)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


# Load the encryption key from the XML key store.
def _load_key_from_store(image_name: str) -> str:
    path = _key_record_path(image_name)
    if not path.exists():
        raise ValueError(
            f"A key must be supplied to decrypt {image_name}; no stored key found."
        )

    tree = ET.parse(path)
    recorded_name = tree.findtext("image") or image_name
    if Path(recorded_name).name != Path(image_name).name:
        raise ValueError("Stored key record does not match the requested image.")
    key_text = tree.findtext("key")
    if not key_text:
        raise ValueError("Stored key file is missing a <key> entry.")
    return key_text.strip()


# Build the sidecar metadata path for an encrypted image.
def _metadata_path_for(image_path: Path) -> Path:
    return image_path.with_suffix(image_path.suffix + ".roi")


# Resolve provided coordinates or fall back to the fixed ROI.
def _resolve_coordinates(
    image_size: Tuple[int, int], coordinates: Iterable[Coordinate] | None
) -> Tuple[Coordinate, ...]:
    if coordinates is None:
        base = tuple(_fixed_roi(image_size))
    else:
        base = tuple(coordinates)
    return tuple(_valid_coordinates(image_size, base))


# Merge boxes into coordinates or pass through explicit coordinates.
def _merge_roi_coordinates(
    coordinates: Iterable[Coordinate] | None,
    boxes: Iterable[Tuple[Coordinate, Coordinate]] | None,
    image_name: str,
) -> Iterable[Coordinate] | None:
    if coordinates is None and boxes is None:
        return None
    if coordinates is not None and boxes is not None:
        raise ValueError(
            f"Provide either coordinates or boxes for {image_name}, not both."
        )
    if boxes is None:
        return coordinates

    merged: list[Coordinate] = []
    for top_left, bottom_right in boxes:
        merged.extend(box_coordinates(top_left, bottom_right))
    return merged


# Capture original pixel values for the ROI.
def _capture_pixel_data(pixels, coordinates: Sequence[Coordinate]) -> dict:
    return {
        "coordinates": [[x, y] for x, y in coordinates],
        "values": [_encode_pixel(pixels[x, y]) for x, y in coordinates],
    }


# Restore pixel values from encrypted metadata.
def _restore_pixel_data(
    pixels, coordinates: Sequence[Coordinate], encoded_values: Sequence[dict]
) -> None:
    if len(coordinates) != len(encoded_values):
        raise ValueError("Corrupted metadata: coordinates and values length mismatch.")
    for (x, y), encoded in zip(coordinates, encoded_values):
        pixels[x, y] = _decode_pixel(encoded)


# Encode a pixel into a JSON-friendly structure.
def _encode_pixel(value) -> dict:
    if isinstance(value, int):
        return {"type": "int", "value": int(value)}
    return {"type": "seq", "value": list(value)}


# Decode a pixel from the JSON-friendly structure.
def _decode_pixel(encoded: dict):
    if encoded["type"] == "int":
        return int(encoded["value"])
    return tuple(encoded["value"])


# Blur only the ROI area using a mask.
def _apply_blur(
    image: Image.Image, coordinates: Sequence[Coordinate], radius: int = 18
) -> None:
    mask = Image.new("L", image.size, 0)
    mask_pixels = mask.load()
    for x, y in coordinates:
        mask_pixels[x, y] = 255

    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    image.paste(blurred, mask=mask)


# Encrypt and write ROI metadata to disk.
def _write_metadata(path: Path, payload: dict, key: str) -> None:
    data = json.dumps(payload).encode("utf-8")
    ciphertext = _crypt_bytes(data, key)
    path.write_bytes(ciphertext)


# Read and decrypt ROI metadata from disk.
def _read_metadata(path: Path, key: str) -> dict:
    ciphertext = path.read_bytes()
    plaintext = _crypt_bytes(ciphertext, key)
    return json.loads(plaintext.decode("utf-8"))


# Core encrypt flow: store metadata + blur ROI.
def _encrypt_flow(
    source_path: Path,
    target_path: Path,
    coordinates: Iterable[Coordinate] | None,
    key: str,
) -> EncryptionResult:
    with Image.open(source_path) as original:
        original.load()
        working = original.copy()

    valid_coordinates = _resolve_coordinates(working.size, coordinates)
    if not valid_coordinates:
        raise ValueError("No valid coordinates were provided.")

    metadata_path = _metadata_path_for(target_path)
    pixel_payload = _capture_pixel_data(working.load(), valid_coordinates)
    _write_metadata(metadata_path, pixel_payload, key)
    key_record_path = _write_key_record(target_path.name, key)
    _apply_blur(working, valid_coordinates)

    working.save(target_path)
    return EncryptionResult(
        working,
        valid_coordinates,
        target_path,
        key,
        metadata_path=metadata_path,
        key_record_path=key_record_path,
    )


# Core decrypt flow: restore ROI from metadata.
def _decrypt_flow(
    source_path: Path,
    target_path: Path,
    coordinates: Iterable[Coordinate] | None,
    key: str,
) -> EncryptionResult:
    metadata_path = _metadata_path_for(source_path)
    key_record_path = _key_record_path(source_path.name)
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file missing for {source_path.name}. Expected {metadata_path.name}"
        )

    payload = _read_metadata(metadata_path, key)
    with Image.open(source_path) as encrypted_img:
        encrypted_img.load()
        working = encrypted_img.copy()

    stored_coordinates = [tuple(coord) for coord in payload["coordinates"]]
    if coordinates is not None:
        provided = tuple(_valid_coordinates(working.size, coordinates))
        if provided != tuple(stored_coordinates):
            raise ValueError(
                "Provided coordinates do not match the encrypted metadata. "
                "Omit coordinates to use the stored ROI."
            )

    restored_coordinates = tuple(stored_coordinates)
    _restore_pixel_data(working.load(), restored_coordinates, payload["values"])
    working.save(target_path)
    return EncryptionResult(
        working,
        restored_coordinates,
        target_path,
        key,
        metadata_path=metadata_path,
        key_record_path=key_record_path if key_record_path.exists() else None,
    )


# Filter out-of-bounds and duplicate coordinates.
def _valid_coordinates(
    size: Tuple[int, int], coordinates: Iterable[Coordinate]
) -> Iterator[Coordinate]:
    width, height = size
    seen: Set[Coordinate] = set()
    for x, y in coordinates:
        if not (0 <= x < width and 0 <= y < height):
            continue
        if (x, y) in seen:
            continue
        seen.add((x, y))
        yield (x, y)


# Derive a 256-bit AES key from text.
def _derive_key(key: str) -> bytes:
    return hashlib.sha256(key.encode("utf-8")).digest()


# Derive a deterministic IV for AES-CTR from text.
def _derive_iv(key: str) -> bytes:
    return hashlib.sha256((key + "|iv").encode("utf-8")).digest()[:16]


# Encrypt/decrypt bytes using AES-CTR.
def _crypt_bytes(data: bytes, key: str) -> bytes:
    key_bytes = _derive_key(key)
    iv = _derive_iv(key)
    counter = Counter.new(128, initial_value=int.from_bytes(iv, "big"))
    cipher = AES.new(key_bytes, AES.MODE_CTR, counter=counter)
    return cipher.encrypt(data)


# Generate a random key for encryption.
def generate_key() -> str:
    """Return a random 256-bit key encoded as hex text."""

    return secrets.token_hex(32)


# Build the default fixed ROI, clamped to image bounds.
def _fixed_roi(image_size: Tuple[int, int]) -> Iterator[Coordinate]:
    width, height = image_size
    (x0, y0), (x1, y1) = FIXED_ROI
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    if x0 > x1 or y0 > y1:
        raise ValueError("Image is too small for the default ROI; adjust FIXED_ROI.")
    return box_coordinates((x0, y0), (x1, y1))


__all__ = [
    "Coordinate",
    "EncryptionResult",
    "box_coordinates",
    "decrypt_image",
    "encrypt_image",
    "generate_key",
    "ensure_directories",
    "IMAGES_ROOT",
    "KEY_DIR",
    "FIXED_ROI",
    "decrypt_image_stream",
]

def decrypt_image_stream(
    image_bytes: bytes,
    metadata_bytes: bytes,
    key: str
) -> Image.Image:
    """
    Decrypts an image entirely in memory using the provided key and metadata bytes.
    This ensures the decrypted image never touches the hard drive.
    """
    # 1. Load the encrypted image from RAM
    encrypted_img = Image.open(io.BytesIO(image_bytes))
    encrypted_img.load()
    working = encrypted_img.copy()

    # 2. Read the metadata payload from RAM
    plaintext = _crypt_bytes(metadata_bytes, key)
    payload = json.loads(plaintext.decode("utf-8"))

    # 3. Restore the pixels
    stored_coordinates = [tuple(coord) for coord in payload["coordinates"]]
    restored_coordinates = tuple(stored_coordinates)
    
    _restore_pixel_data(working.load(), restored_coordinates, payload["values"])
    
    # Return the PIL Image object (still in memory)
    return working
