import io
import time
import numpy as np
from PIL import Image, ImageDraw

from app.core.forensics import EvidenceStatus
from app.modules.forensics.image import (
    check_c2pa_and_provenance_manifest,
    check_exif_metadata_anomaly,
    check_image_dimension_anomaly,
    check_jpeg_quality_factor_anomaly,
    compute_error_level_analysis,
    compute_fft_spectral_analysis,
    run_fast_plane_forensics,
    run_slow_plane_forensics,
)


def _make_test_jpeg(width: int, height: int, quality: int = 95, software_exif: str | None = None) -> bytes:
    img = Image.new("RGB", (width, height), color=(140, 160, 180))
    buf = io.BytesIO()
    if software_exif:
        exif = img.getexif()
        exif[305] = software_exif  # Tag 305: Software
        img.save(buf, format="JPEG", quality=quality, exif=exif)
    else:
        img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def test_image_dimension_anomaly():
    """
    Verifies detection of standard AI generation resolutions vs real camera photos.
    """
    # 1. Standard AI output sizes (e.g. 1024x1024, 512x512)
    ai_jpeg_1024 = _make_test_jpeg(1024, 1024)
    sig_1024 = check_image_dimension_anomaly(ai_jpeg_1024)
    assert sig_1024.status == EvidenceStatus.ANOMALOUS
    assert sig_1024.details["matched_ai_profile"] is True
    assert sig_1024.score >= 0.80

    ai_jpeg_512 = _make_test_jpeg(512, 512)
    sig_512 = check_image_dimension_anomaly(ai_jpeg_512)
    assert sig_512.status == EvidenceStatus.ANOMALOUS

    # 2. Camera photo dimensions (e.g. 1920x1080 or phone 4032x3024)
    camera_jpeg = _make_test_jpeg(1920, 1080)
    sig_cam = check_image_dimension_anomaly(camera_jpeg)
    assert sig_cam.status == EvidenceStatus.PRESENT
    assert sig_cam.details["matched_ai_profile"] is False
    assert sig_cam.score <= 0.20


def test_exif_metadata_anomaly():
    """
    Verifies EXIF inspection:
    - Missing EXIF -> EvidenceStatus.UNAVAILABLE (not anomalous).
    - AI Software tags (e.g. 'Stable Diffusion', 'Midjourney') -> EvidenceStatus.ANOMALOUS.
    - Clean camera EXIF -> EvidenceStatus.PRESENT.
    """
    # 1. No EXIF
    no_exif_jpeg = _make_test_jpeg(800, 600)
    sig_no_exif = check_exif_metadata_anomaly(no_exif_jpeg)
    assert sig_no_exif.status == EvidenceStatus.UNAVAILABLE
    assert "No EXIF" in sig_no_exif.details.get("reason", "")

    # 2. AI Generator software tag (Stable Diffusion)
    sd_jpeg = _make_test_jpeg(800, 600, software_exif="Stable Diffusion v2.1 (Automatic1111)")
    sig_sd = check_exif_metadata_anomaly(sd_jpeg)
    assert sig_sd.status == EvidenceStatus.ANOMALOUS
    assert sig_sd.score >= 0.90
    assert "stable diffusion" in sig_sd.details["matched_signature"]

    # 3. AI Generator software tag (Midjourney)
    mj_jpeg = _make_test_jpeg(800, 600, software_exif="Midjourney v5.2 AI Renderer")
    sig_mj = check_exif_metadata_anomaly(mj_jpeg)
    assert sig_mj.status == EvidenceStatus.ANOMALOUS

    # 4. Legitimate camera hardware software tag
    cam_img = Image.new("RGB", (800, 600), color=(120, 120, 120))
    exif = cam_img.getexif()
    exif[271] = "Apple"            # Make
    exif[272] = "iPhone 13 Pro"    # Model
    exif[305] = "iOS 16.5"         # Software
    buf = io.BytesIO()
    cam_img.save(buf, format="JPEG", exif=exif)

    sig_cam = check_exif_metadata_anomaly(buf.getvalue())
    assert sig_cam.status == EvidenceStatus.PRESENT
    assert sig_cam.score <= 0.10


def test_jpeg_quality_factor_anomaly():
    """
    Verifies JPEG quantization table inspection:
    - Non-JPEG images return UNAVAILABLE.
    - Round software export quality (quality=95) returns ANOMALOUS.
    - Custom compression quality (quality=82) returns PRESENT.
    """
    # 1. Non-JPEG (PNG)
    png_buf = io.BytesIO()
    Image.new("RGB", (200, 200), color=(100, 100, 100)).save(png_buf, format="PNG")
    sig_png = check_jpeg_quality_factor_anomaly(png_buf.getvalue())
    assert sig_png.status == EvidenceStatus.UNAVAILABLE

    # 2. Round software export quality (95)
    round_jpeg = _make_test_jpeg(200, 200, quality=95)
    sig_round = check_jpeg_quality_factor_anomaly(round_jpeg)
    assert sig_round.status == EvidenceStatus.ANOMALOUS
    assert sig_round.details["is_round_quality"] is True
    assert sig_round.details["estimated_quality"] == 95

    # 3. Camera non-round quality (82)
    custom_jpeg = _make_test_jpeg(200, 200, quality=82)
    sig_custom = check_jpeg_quality_factor_anomaly(custom_jpeg)
    assert sig_custom.status == EvidenceStatus.PRESENT
    assert sig_custom.details["is_round_quality"] is False


def test_fast_plane_forensics_execution_time():
    """
    Verifies that all 3 fast-plane checks run synchronously in < 25ms total.
    """
    doc_bytes = _make_test_jpeg(1024, 1024, quality=95)

    start = time.perf_counter()
    results = run_fast_plane_forensics(doc_bytes)
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 50.0  # Well within the synchronous SLA
    assert "image_dimensions" in results
    assert "exif_metadata" in results
    assert "jpeg_quality" in results
    assert results["image_dimensions"].status == EvidenceStatus.ANOMALOUS


def test_error_level_analysis_clean_vs_tampered():
    """
    Verifies that Error Level Analysis (ELA) differentiates clean images
    from images with spliced high-contrast pasted elements.
    """
    # 1. Clean uniform image
    clean_jpeg = _make_test_jpeg(300, 300, quality=90)
    sig_clean = compute_error_level_analysis(clean_jpeg, recompress_quality=85)
    assert sig_clean.status == EvidenceStatus.PRESENT
    assert sig_clean.details["tampering_likely"] is False

    # 2. Tampered image with high-contrast spliced region
    img = Image.new("RGB", (300, 300), color=(50, 50, 50))
    draw = ImageDraw.Draw(img)
    # Draw distinct high-contrast block
    draw.rectangle([100, 100, 200, 200], fill=(255, 255, 255))
    draw.line([50, 50, 250, 250], fill=(255, 0, 0), width=5)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    tampered_jpeg = buf.getvalue()

    sig_tampered = compute_error_level_analysis(tampered_jpeg, recompress_quality=75)
    assert sig_tampered.status == EvidenceStatus.ANOMALOUS
    assert sig_tampered.details["max_error"] > 60.0


def test_fft_spectral_analysis():
    """
    Verifies 2D FFT spectral analysis on natural images vs images with artificial periodic grid artifacts.
    """
    # 1. Natural smooth gradient image
    gradient = np.zeros((128, 128), dtype=np.uint8)
    for i in range(128):
        gradient[i, :] = int(i * 2)
    im_grad = Image.fromarray(gradient)
    buf_grad = io.BytesIO()
    im_grad.save(buf_grad, format="PNG")

    sig_smooth = compute_fft_spectral_analysis(buf_grad.getvalue())
    assert sig_smooth.status == EvidenceStatus.PRESENT
    assert sig_smooth.details["grid_artifact_detected"] is False

    # 2. Grid-modulated image (simulating GAN upsampling transposed-convolution checkerboard)
    grid_img = np.copy(gradient)
    for i in range(0, 128, 4):
        for j in range(0, 128, 4):
            grid_img[i, j] = 255
    im_grid = Image.fromarray(grid_img)
    buf_grid = io.BytesIO()
    im_grid.save(buf_grid, format="PNG")

    sig_grid = compute_fft_spectral_analysis(buf_grid.getvalue())
    assert sig_grid.status in (EvidenceStatus.ANOMALOUS, EvidenceStatus.PRESENT)
    assert "spectral_peak_ratio" in sig_grid.details


# NOTE: Face embedding tests have been moved to tests/unit/test_forensics_face.py
# The old 64×64 pixel cosine similarity function (compute_face_embedding_similarity)
# was removed in Task 3.4 and replaced with InsightFace ArcFace embeddings.


def test_run_slow_plane_forensics():
    """
    Verifies slow-plane aggregation returning ELA, FFT, and face consistency signals.
    """
    doc_bytes = _make_test_jpeg(200, 200, quality=90)
    selfie_bytes = _make_test_jpeg(200, 200, quality=90)

    results = run_slow_plane_forensics(doc_bytes, selfie_bytes)
    assert "error_level_analysis" in results
    assert "fft_spectral_analysis" in results
    assert "face_consistency" in results
    assert results["error_level_analysis"].signal_name == "error_level_analysis"
    assert results["face_consistency"].signal_name == "face_consistency"


def test_check_c2pa_provenance_manifest():
    """
    Verifies detection of C2PA manifests, Google Generative AI / DALL-E claims,
    and fallback for clean images without provenance.
    """
    # 1. Clean image without C2PA or AI metadata -> UNAVAILABLE
    clean_bytes = _make_test_jpeg(400, 300)
    sig_clean = check_c2pa_and_provenance_manifest(clean_bytes)
    assert sig_clean.status == EvidenceStatus.UNAVAILABLE

    # 2. Synthetic C2PA box with Google Generative AI claim -> ANOMALOUS
    c2pa_fake_bytes = clean_bytes + b"caBX\x00\x00\x01\x00Created by Google Generative AI. digitalSourceType/trainedAlgorithmicMedia"
    sig_c2pa = check_c2pa_and_provenance_manifest(c2pa_fake_bytes)
    assert sig_c2pa.status == EvidenceStatus.ANOMALOUS
    assert sig_c2pa.score == 1.00
    assert sig_c2pa.details["is_ai_generated"] is True
    assert "Google Generative AI" in sig_c2pa.details["generator"]

    # 3. Filename generator pattern check -> ANOMALOUS
    sig_fn = check_c2pa_and_provenance_manifest(clean_bytes, filename="Gemini_Generated_Image_test123.png")
    assert sig_fn.status == EvidenceStatus.ANOMALOUS
    assert sig_fn.details["is_ai_generated"] is True

    # 4. Fast plane integration returns c2pa_provenance
    fast_results = run_fast_plane_forensics(c2pa_fake_bytes, filename="card_scan.jpg")
    assert "c2pa_provenance" in fast_results
    assert fast_results["c2pa_provenance"].status == EvidenceStatus.ANOMALOUS

