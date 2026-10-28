import io
import logging

import numpy as np
from PIL import Image, ImageChops

from app.core.forensics import EvidenceStatus, TamperingSignal

logger = logging.getLogger(__name__)

# Known AI generator fixed output dimensions (Stable Diffusion, Midjourney, DALL-E, Flux, Imagen 2)
KNOWN_AI_RESOLUTIONS = {
    (1024, 1024),
    (512, 512),
    (768, 768),
    (512, 768),
    (768, 512),
    (1024, 768),
    (768, 1024),
    (1536, 1024),
    (1024, 1536),
    (896, 1152),
    (1152, 896),
    (1408, 768),  # Google Imagen 2 / Gemini widescreen 16:9
    (768, 1408),  # Google Imagen 2 / Gemini portrait 9:16
    (1344, 768),
    (768, 1344),
    (1024, 576),
    (576, 1024),
}

# Known AI tool / generative software signatures in EXIF Software or Artist tags
AI_SOFTWARE_SIGNATURES = [
    "stable diffusion",
    "midjourney",
    "dall-e",
    "dalle",
    "adobe firefly",
    "firefly",
    "photoshop",
    "gimp",
    "comfyui",
    "automatic1111",
    "invokeai",
    "novelai",
    "flux.1",
    "gemini",
    "google generative ai",
    "google c2pa",
    "imagen",
    "synthid",
]

# Standard baseline luminance quantization table at Quality 50 (ITU-T T.81 / ISO 10918-1)
_STD_LUMINANCE_QUANT_TABLE = (
    16, 11, 10, 16, 24, 40, 51, 61,
    12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56,
    14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77,
    24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101,
    72, 92, 95, 98, 112, 100, 103, 99,
)


def _load_image(image_input: Image.Image | bytes) -> Image.Image:
    if isinstance(image_input, Image.Image):
        return image_input
    return Image.open(io.BytesIO(image_input))


# --- P0 Fast Plane Signals (< 10ms, Pillow only, synchronous) ---

def check_c2pa_and_provenance_manifest(
    image_input: Image.Image | bytes,
    filename: str = "",
) -> TamperingSignal:
    """
    Inspects image for Coalition for Content Provenance and Authenticity (C2PA) / Content Credentials
    manifests (ISO/IEC 19566-5 JUMBF containers in PNG caBX/caIp chunks and JPEG APP11 markers),
    generative AI text chunks (parameters, prompt, workflow), and cryptographic provenance declarations.
    """
    try:
        raw_bytes: bytes
        if isinstance(image_input, bytes):
            raw_bytes = image_input
            img = _load_image(image_input)
        else:
            img = image_input
            buf = io.BytesIO()
            fmt = img.format or "PNG"
            img.save(buf, format=fmt)
            raw_bytes = buf.getvalue()

        claims: list[str] = []
        generator: str | None = None
        has_c2pa_container = (
            b"caBX" in raw_bytes
            or b"caIp" in raw_bytes
            or b"c2pa" in raw_bytes
            or b"\xff\xeb" in raw_bytes  # JPEG APP11 marker
            or b"jumd" in raw_bytes      # JUMBF description box
        )

        # 1. Official IPTC digital source type assertion for AI-generated media
        if b"trainedAlgorithmicMedia" in raw_bytes:
            claims.append("IPTC digitalSourceType: trainedAlgorithmicMedia (AI-generated)")

        # 2. Generator-specific C2PA claims and cryptographic certificates
        if (
            b"Created by Google Generative AI" in raw_bytes
            or b"Google C2PA Core Generator" in raw_bytes
            or b"Google C2PA Media Services" in raw_bytes
        ):
            generator = "Google Generative AI (Gemini / Imagen)"
            claims.append("Google C2PA Cryptographic Provenance Manifest")
        elif b"DALL-E" in raw_bytes or b"dall-e" in raw_bytes:
            generator = "OpenAI DALL-E"
            claims.append("OpenAI Provenance Signature (C2PA)")
        elif b"Adobe Firefly" in raw_bytes or b"Firefly" in raw_bytes:
            generator = "Adobe Firefly"
            claims.append("Adobe Content Credentials (C2PA)")
        elif b"Midjourney" in raw_bytes:
            generator = "Midjourney"
            claims.append("Midjourney Generative Signature")
        elif b"Microsoft Copilot" in raw_bytes or b"BingImageCreator" in raw_bytes:
            generator = "Microsoft Designer / Copilot"
            claims.append("Microsoft C2PA Provenance Signature")

        # 3. Inspect PNG metadata chunks (tEXt, iTXt, zTXt)
        for k, v in getattr(img, "info", {}).items():
            k_lower = str(k).lower()
            v_str = str(v)
            if k_lower in ("parameters", "prompt", "workflow", "comment"):
                for tool in ("automatic1111", "comfyui", "novelai", "stable diffusion", "flux"):
                    if tool in v_str.lower() or tool in k_lower:
                        if not generator:
                            generator = tool.title()
                        claims.append(f"PNG {k} chunk declares generative pipeline ({tool})")

        # 4. Filename inspection for known AI generation patterns
        if filename:
            fn_lower = filename.lower()
            for pattern in ("gemini_generated", "dall", "midjourney", "stablediffusion", "flux"):
                if pattern in fn_lower:
                    claims.append(f"Filename matches AI generator export pattern ({filename})")
                    if not generator:
                        generator = "Generative AI Tool"

        if claims or (has_c2pa_container and generator):
            gen_label = generator or "Generative AI Model"
            return TamperingSignal(
                signal_name="c2pa_provenance",
                status=EvidenceStatus.ANOMALOUS,
                score=1.00,
                details={
                    "is_ai_generated": True,
                    "generator": gen_label,
                    "has_c2pa_container": has_c2pa_container,
                    "matched_claims": claims,
                    "reason": f"Cryptographic provenance confirms media was generated by {gen_label}.",
                },
            )

        if has_c2pa_container:
            return TamperingSignal(
                signal_name="c2pa_provenance",
                status=EvidenceStatus.PRESENT,
                score=0.05,
                details={
                    "is_ai_generated": False,
                    "has_c2pa_container": True,
                    "reason": "C2PA manifest container present without generative AI claims.",
                },
            )

        return TamperingSignal(
            signal_name="c2pa_provenance",
            status=EvidenceStatus.UNAVAILABLE,
            details={
                "reason": "No C2PA provenance manifest or generative tool metadata detected (metadata may have been stripped).",
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="c2pa_provenance",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def check_image_dimension_anomaly(image_input: Image.Image | bytes) -> TamperingSignal:
    """
    Checks pixel dimensions against standard AI generator output resolutions.
    Physical camera photos are typically high-megapixel non-square images (e.g. 4032x3024).
    """
    try:
        img = _load_image(image_input)
        size = img.size  # (width, height)

        if size in KNOWN_AI_RESOLUTIONS:
            return TamperingSignal(
                signal_name="image_dimensions",
                status=EvidenceStatus.ANOMALOUS,
                score=0.85,
                details={
                    "width": size[0],
                    "height": size[1],
                    "aspect_ratio": round(size[0] / size[1], 2),
                    "matched_ai_profile": True,
                    "reason": f"Exact match for standard generative AI canvas resolution {size[0]}x{size[1]}.",
                },
            )

        return TamperingSignal(
            signal_name="image_dimensions",
            status=EvidenceStatus.PRESENT,
            score=0.1,
            details={
                "width": size[0],
                "height": size[1],
                "aspect_ratio": round(size[0] / size[1], 2),
                "matched_ai_profile": False,
                "reason": f"Non-preset resolution {size[0]}x{size[1]}. Note: Dimension check is a screening heuristic; genuine authenticity requires C2PA or cryptographic QR.",
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="image_dimensions",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def check_exif_metadata_anomaly(image_input: Image.Image | bytes) -> TamperingSignal:
    """
    Inspects image EXIF tags for camera hardware metadata vs AI generation tool signatures.
    Per FORENSICS_DESIGN.md §2.2, missing EXIF is recorded as UNAVAILABLE, not anomalous.
    """
    try:
        img = _load_image(image_input)
        exif = img.getexif()

        if not exif or len(exif) == 0:
            return TamperingSignal(
                signal_name="exif_metadata",
                status=EvidenceStatus.UNAVAILABLE,
                details={"reason": "No EXIF metadata present (common in web uploads and social messaging)."},
            )

        # Inspect common software/creator tags: 305 (Software), 315 (Artist), 270 (ImageDescription)
        software_str = str(exif.get(305, "")).lower()
        artist_str = str(exif.get(315, "")).lower()
        make_str = str(exif.get(271, ""))
        model_str = str(exif.get(272, ""))

        combined_tags = f"{software_str} {artist_str}"
        for sig in AI_SOFTWARE_SIGNATURES:
            if sig in combined_tags:
                return TamperingSignal(
                    signal_name="exif_metadata",
                    status=EvidenceStatus.ANOMALOUS,
                    score=0.95,
                    details={
                        "matched_signature": sig,
                        "software": software_str,
                        "make": make_str,
                        "model": model_str,
                        "reason": f"EXIF metadata indicates generation or editing with '{sig}'.",
                    },
                )

        return TamperingSignal(
            signal_name="exif_metadata",
            status=EvidenceStatus.PRESENT,
            score=0.05,
            details={
                "make": make_str,
                "model": model_str,
                "software": software_str,
                "total_tags": len(exif),
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="exif_metadata",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def check_jpeg_quality_factor_anomaly(image_input: Image.Image | bytes) -> TamperingSignal:
    """
    Estimates JPEG compression quality factor from quantization tables.
    Round integer qualities (e.g. exactly 90, 95, 100) are characteristic of software exporters.
    """
    try:
        img = _load_image(image_input)
        if img.format != "JPEG" and not hasattr(img, "quantization"):
            return TamperingSignal(
                signal_name="jpeg_quality",
                status=EvidenceStatus.UNAVAILABLE,
                details={"format": img.format or "unknown", "reason": "Not a JPEG image; quantization tables unavailable."},
            )

        tables = getattr(img, "quantization", None)
        if not tables or 0 not in tables:
            return TamperingSignal(
                signal_name="jpeg_quality",
                status=EvidenceStatus.UNAVAILABLE,
                details={"reason": "Quantization table #0 missing."},
            )

        lum_table = tables[0]
        ratios = [
            t / base
            for t, base in zip(lum_table, _STD_LUMINANCE_QUANT_TABLE)
            if base > 0
        ]
        avg_ratio = sum(ratios) / len(ratios)
        scale = avg_ratio * 100
        if scale <= 100:
            quality = round((200 - scale) / 2)
        else:
            quality = round(5000 / scale)
        quality = max(1, min(100, quality))

        # Check for suspiciously round quality factor typical of AI generation tools
        is_round = quality in (85, 90, 95, 100)
        status = EvidenceStatus.ANOMALOUS if (is_round and quality >= 90) else EvidenceStatus.PRESENT

        return TamperingSignal(
            signal_name="jpeg_quality",
            status=status,
            score=round(quality / 100.0, 2),
            details={
                "estimated_quality": quality,
                "is_round_quality": is_round,
                "reason": "Round software export quality factor detected." if is_round else "Standard compression profile.",
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="jpeg_quality",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def run_fast_plane_forensics(
    document_bytes: bytes,
    filename: str = "",
) -> dict[str, TamperingSignal]:
    """
    Executes synchronous fast-plane checks in < 15ms total without GPU or neural models.
    Evaluates C2PA cryptographic provenance, AI software metadata, EXIF, dimensions, and JPEG quantization.
    """
    return {
        "c2pa_provenance": check_c2pa_and_provenance_manifest(document_bytes, filename),
        "image_dimensions": check_image_dimension_anomaly(document_bytes),
        "exif_metadata": check_exif_metadata_anomaly(document_bytes),
        "jpeg_quality": check_jpeg_quality_factor_anomaly(document_bytes),
    }


# --- P1 Slow Plane Signals (CPU-feasible worker jobs) ---

def compute_error_level_analysis(
    image_bytes: bytes, recompress_quality: int = 90
) -> TamperingSignal:
    """
    Error Level Analysis (ELA): Computes differential error between original JPEG and recompressed version.
    Spliced or copy-pasted document elements compress at different error levels than original photo content.
    """
    try:
        orig = _load_image(image_bytes).convert("RGB")
        buf = io.BytesIO()
        orig.save(buf, format="JPEG", quality=recompress_quality)
        buf.seek(0)
        recompressed = Image.open(buf).convert("RGB")

        diff = ImageChops.difference(orig, recompressed)
        stat = np.array(diff, dtype=np.float32)

        mean_diff = float(np.mean(stat))
        max_diff = float(np.max(stat))
        p95_diff = float(np.percentile(stat, 95))

        # Anomalous if localized error spikes indicate copy-paste paste artifacts
        is_anomalous = max_diff > 60.0 and (max_diff / (mean_diff + 1e-6) > 15.0 or p95_diff > 10.0)
        status = EvidenceStatus.ANOMALOUS if is_anomalous else EvidenceStatus.PRESENT

        return TamperingSignal(
            signal_name="error_level_analysis",
            status=status,
            score=round(min(1.0, max_diff / 100.0), 4),
            details={
                "mean_error": round(mean_diff, 4),
                "max_error": round(max_diff, 4),
                "p95_error": round(p95_diff, 4),
                "tampering_likely": is_anomalous,
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="error_level_analysis",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def compute_fft_spectral_analysis(image_bytes: bytes) -> TamperingSignal:
    """
    2D Fast Fourier Transform Spectral Analysis:
    Detects periodic grid artifacts and high-frequency harmonics left by transposed-convolution upsampling
    in GAN and synthetic facial generators.
    """
    try:
        img = _load_image(image_bytes).convert("L")
        arr = np.array(img, dtype=np.float32)

        if arr.shape[0] < 32 or arr.shape[1] < 32:
            return TamperingSignal(
                signal_name="fft_spectral_analysis",
                status=EvidenceStatus.UNAVAILABLE,
                details={"reason": "Image too small for spectral analysis."},
            )

        # 2D FFT and center DC component
        f = np.fft.fft2(arr)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = np.log(np.abs(fshift) + 1e-9)

        h, w = magnitude_spectrum.shape
        cy, cx = h // 2, w // 2

        # Exclude DC center component (radius 4) to focus on mid-high frequency grid anomalies
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        high_freq_mask = dist_from_center > 10

        if not np.any(high_freq_mask):
            return TamperingSignal(
                signal_name="fft_spectral_analysis",
                status=EvidenceStatus.UNAVAILABLE,
                details={"reason": "Insufficient spatial frequency bins."},
            )

        high_freq_vals = magnitude_spectrum[high_freq_mask]
        mean_power = float(np.mean(high_freq_vals))
        max_power = float(np.max(high_freq_vals))
        ratio = max_power / (mean_power + 1e-9)

        # High localized spectral spikes relative to background indicate artificial upsampling grid
        is_anomalous = ratio > 2.80
        status = EvidenceStatus.ANOMALOUS if is_anomalous else EvidenceStatus.PRESENT

        return TamperingSignal(
            signal_name="fft_spectral_analysis",
            status=status,
            score=round(min(1.0, ratio / 3.0), 4),
            details={
                "spectral_peak_ratio": round(ratio, 4),
                "mean_power": round(mean_power, 4),
                "max_power": round(max_power, 4),
                "grid_artifact_detected": is_anomalous,
            },
        )
    except Exception as e:
        return TamperingSignal(
            signal_name="fft_spectral_analysis",
            status=EvidenceStatus.UNAVAILABLE,
            details={"error": str(e)},
        )


def run_slow_plane_forensics(
    document_bytes: bytes,
    selfie_bytes: bytes | None = None,
) -> dict[str, TamperingSignal]:
    """
    Executes slow-plane forensic tasks (ELA, FFT, ArcFace face consistency)
    during asynchronous worker jobs.

    Face comparison now uses InsightFace buffalo_sc ArcFace embeddings (512-d)
    via app.modules.forensics.face. The old 64×64 pixel cosine similarity path
    has been removed — it produced unreliable signals (Task 3.4).
    """
    from app.modules.forensics.face import compare_face_embeddings

    signals = {
        "error_level_analysis": compute_error_level_analysis(document_bytes),
        "fft_spectral_analysis": compute_fft_spectral_analysis(document_bytes),
    }
    if selfie_bytes:
        signals["face_consistency"] = compare_face_embeddings(document_bytes, selfie_bytes)
    else:
        signals["face_consistency"] = TamperingSignal(
            signal_name="face_consistency",
            status=EvidenceStatus.UNAVAILABLE,
            details={"reason": "Selfie image not supplied for cross-biometric comparison."},
        )
    return signals
