"""Theme-colour extraction for managed Dashboard wallpapers."""

from __future__ import annotations

import colorsys
from collections.abc import Iterable
from dataclasses import dataclass
from typing import cast

from PIL import Image

DEFAULT_THEME_COLORS = ("#3c96ca", "#2f86bd")
_MAX_SAMPLE_PIXELS = 24_000
_QUANTIZE_COLORS = 12


@dataclass(frozen=True)
class ThemeColors:
    """Primary and secondary colours suitable for Dashboard UI surfaces."""

    primary: str
    secondary: str


@dataclass(frozen=True)
class _ColorCandidate:
    rgb: tuple[int, int, int]
    count: int
    saturation: float
    lightness: float


def extract_theme_colors(image: Image.Image) -> ThemeColors:
    """Extract a readable primary/secondary pair from a small preview image.

    The input is expected to be the generated thumbnail, not the original
    wallpaper, so colour extraction never forces a second full-size decode.

    Args:
        image: Decoded preview image. Animated images use their current frame.

    Returns:
        Normalised primary and secondary colours, or the defaults when the
        preview has no usable colour candidates.
    """

    candidates = _collect_candidates(image)
    if not candidates:
        return ThemeColors(*DEFAULT_THEME_COLORS)

    primary = _select_primary(candidates)
    secondary = _select_secondary(candidates, primary)
    return ThemeColors(
        primary=_rgb_to_hex(_normalize_ui_color(primary.rgb)),
        secondary=_rgb_to_hex(_normalize_ui_color(secondary.rgb)),
    )


def _collect_candidates(image: Image.Image) -> list[_ColorCandidate]:
    preview = image.convert("RGBA")
    preview.thumbnail((160, 160))

    pixels: list[tuple[int, int, int]] = []
    flattened = getattr(preview, "get_flattened_data", None)
    pixel_data = cast(
        Iterable[tuple[int, int, int, int]],
        flattened() if callable(flattened) else preview.getdata(),
    )
    for red, green, blue, alpha in pixel_data:
        if alpha < 32 or len(pixels) >= _MAX_SAMPLE_PIXELS:
            continue
        _, lightness, _ = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
        if lightness < 0.06 or lightness > 0.94:
            continue
        pixels.append((red, green, blue))

    if not pixels:
        return []

    palette_image = Image.new("RGB", (len(pixels), 1))
    palette_image.putdata(pixels)
    quantized = palette_image.quantize(
        colors=_QUANTIZE_COLORS,
        method=Image.Quantize.MEDIANCUT,
    )
    palette = quantized.getpalette()
    if palette is None:
        return []

    total = len(pixels)
    candidates: list[_ColorCandidate] = []
    for count, raw_index in quantized.getcolors(maxcolors=_QUANTIZE_COLORS) or []:
        if raw_index is None:
            continue
        offset = cast(int, raw_index) * 3
        rgb = tuple(int(channel) for channel in palette[offset : offset + 3])
        if len(rgb) != 3:
            continue
        _, lightness, saturation = colorsys.rgb_to_hls(
            rgb[0] / 255,
            rgb[1] / 255,
            rgb[2] / 255,
        )
        if count / total < 0.015:
            continue
        if lightness < 0.08 or lightness > 0.92:
            continue
        candidates.append(
            _ColorCandidate(
                rgb=rgb,  # type: ignore[arg-type]
                count=count,
                saturation=saturation,
                lightness=lightness,
            )
        )

    candidates.sort(
        key=lambda item: (
            item.count * (0.55 + item.saturation) * (1.0 - abs(item.lightness - 0.5)),
            item.saturation,
        ),
        reverse=True,
    )
    return candidates


def _select_primary(candidates: list[_ColorCandidate]) -> _ColorCandidate:
    colorful = [candidate for candidate in candidates if candidate.saturation >= 0.18]
    return colorful[0] if colorful else candidates[0]


def _select_secondary(
    candidates: list[_ColorCandidate],
    primary: _ColorCandidate,
) -> _ColorCandidate:
    primary_hue = _hue(primary.rgb)
    alternatives = [
        candidate
        for candidate in candidates
        if candidate.rgb != primary.rgb
        and _hue_distance(primary_hue, _hue(candidate.rgb)) >= 0.08
    ]
    if alternatives:
        alternatives.sort(
            key=lambda item: (
                _hue_distance(primary_hue, _hue(item.rgb)) * 0.65
                + item.saturation * 0.25
                + (item.count / max(primary.count, 1)) * 0.10
            ),
            reverse=True,
        )
        return alternatives[0]
    return _ColorCandidate(
        rgb=_derive_secondary(primary.rgb),
        count=primary.count,
        saturation=primary.saturation,
        lightness=primary.lightness,
    )


def _normalize_ui_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    hue, lightness, saturation = colorsys.rgb_to_hls(
        rgb[0] / 255,
        rgb[1] / 255,
        rgb[2] / 255,
    )
    if saturation < 0.08:
        hue = 0.56
        saturation = 0.30
    saturation = min(max(saturation, 0.34), 0.78)
    lightness = min(max(lightness, 0.38), 0.62)
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (round(red * 255), round(green * 255), round(blue * 255))


def _derive_secondary(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    hue, lightness, saturation = colorsys.rgb_to_hls(
        rgb[0] / 255,
        rgb[1] / 255,
        rgb[2] / 255,
    )
    if saturation < 0.08:
        hue = 0.64
        saturation = 0.30
    else:
        hue = (hue + 0.08) % 1.0
    saturation = min(max(saturation * 0.92, 0.30), 0.72)
    lightness = min(max(lightness * 0.94, 0.34), 0.58)
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return (round(red * 255), round(green * 255), round(blue * 255))


def _hue(rgb: tuple[int, int, int]) -> float:
    hue, _, _ = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    return hue


def _hue_distance(left: float, right: float) -> float:
    distance = abs(left - right)
    return min(distance, 1.0 - distance)


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)
