"""Regression tests for stego capacity behavior.

Why this file exists:
    It protects the core hide/reveal workflows against regressions in capacity
    handling, especially auto bit-depth selection and actionable failure paths.
"""

import math
import random
import tempfile
import unittest
import io
from pathlib import Path

from PIL import Image

from stego import HEADER, hide_image, reveal_image


def _random_rgb_image(width: int, height: int, seed: int) -> Image.Image:
    rng = random.Random(seed)
    pixels = [
        (rng.randrange(256), rng.randrange(256), rng.randrange(256))
        for _ in range(width * height)
    ]
    image = Image.new("RGB", (width, height))
    image.putdata(pixels)
    return image


def _image_bytes(path: Path) -> tuple[str, tuple[int, int], bytes]:
    with Image.open(path) as img:
        img.load()
        return img.mode, img.size, img.tobytes()


class StegoCapacityTests(unittest.TestCase):
    def test_hide_and_reveal_with_fixed_bit_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cover_dir = root / "covers"
            secret_dir = root / "secret"
            hidden_dir = root / "hidden"
            reveal_dir = root / "reveal"
            for path in (cover_dir, secret_dir, hidden_dir, reveal_dir):
                path.mkdir(parents=True, exist_ok=True)

            _random_rgb_image(64, 64, seed=1).save(cover_dir / "cover.png")
            _random_rgb_image(20, 20, seed=2).save(secret_dir / "secret.png")

            hidden_path = hide_image(
                "cover.png",
                "secret.png",
                bits_per_channel=1,
                key="test-key",
                cover_dir=cover_dir,
                secret_dir=secret_dir,
                output_dir=hidden_dir,
            )
            recovered_path = reveal_image(
                hidden_path.name,
                bits_per_channel=None,
                stego_dir=hidden_dir,
                output_dir=reveal_dir,
            )

            self.assertEqual(
                _image_bytes(secret_dir / "secret.png"),
                _image_bytes(recovered_path),
            )

    def test_auto_upgrades_bit_depth_when_one_bit_is_too_small(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cover_dir = root / "covers"
            secret_dir = root / "secret"
            hidden_dir = root / "hidden"
            reveal_dir = root / "reveal"
            for path in (cover_dir, secret_dir, hidden_dir, reveal_dir):
                path.mkdir(parents=True, exist_ok=True)

            key = "auto-key"
            secret_path = secret_dir / "secret.png"
            _random_rgb_image(24, 24, seed=3).save(secret_path)
            with Image.open(secret_path) as secret_image:
                buffer = io.BytesIO()
                secret_image.save(buffer, format="PNG")
                payload_length = len(buffer.getvalue())

            # Compute a cover size that is too small for bpc=1 but large enough for bpc=2.
            required_bits = (HEADER.size + payload_length + len(key.encode("utf-8"))) * 8
            carrier_byte_length = math.ceil(required_bits / 2)
            width = math.ceil(carrier_byte_length / 3)
            _random_rgb_image(width, 1, seed=4).save(cover_dir / "cover.png")

            with self.assertRaisesRegex(ValueError, r"minimum bits_per_channel=2"):
                hide_image(
                    "cover.png",
                    "secret.png",
                    bits_per_channel=1,
                    key=key,
                    cover_dir=cover_dir,
                    secret_dir=secret_dir,
                    output_dir=hidden_dir,
                )

            hidden_path = hide_image(
                "cover.png",
                "secret.png",
                bits_per_channel=None,
                key=key,
                cover_dir=cover_dir,
                secret_dir=secret_dir,
                output_dir=hidden_dir,
            )
            recovered_path = reveal_image(
                hidden_path.name,
                bits_per_channel=None,
                stego_dir=hidden_dir,
                output_dir=reveal_dir,
            )

            self.assertEqual(
                _image_bytes(secret_dir / "secret.png"),
                _image_bytes(recovered_path),
            )

    def test_raises_actionable_error_when_cover_cannot_fit_even_at_eight_bits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cover_dir = root / "covers"
            secret_dir = root / "secret"
            hidden_dir = root / "hidden"
            for path in (cover_dir, secret_dir, hidden_dir):
                path.mkdir(parents=True, exist_ok=True)

            _random_rgb_image(4, 4, seed=5).save(cover_dir / "tiny_cover.png")
            _random_rgb_image(24, 24, seed=6).save(secret_dir / "secret.png")

            with self.assertRaisesRegex(
                ValueError, r"even at bits_per_channel=8.*larger cover image"
            ):
                hide_image(
                    "tiny_cover.png",
                    "secret.png",
                    bits_per_channel=None,
                    key="too-big",
                    cover_dir=cover_dir,
                    secret_dir=secret_dir,
                    output_dir=hidden_dir,
                )


if __name__ == "__main__":
    unittest.main()
