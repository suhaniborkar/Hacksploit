from app.modules.forensics.image import (
    check_exif_metadata_anomaly,
    check_image_dimension_anomaly,
    check_jpeg_quality_factor_anomaly,
    compute_error_level_analysis,
    compute_fft_spectral_analysis,
    run_fast_plane_forensics,
    run_slow_plane_forensics,
)
from app.modules.forensics.face import (
    compare_face_embeddings,
    compute_face_embedding,
)
from app.modules.forensics.ocr import (
    FieldContradictionDetector,
    OCRExtractor,
    compare_dobs,
    compute_verhoeff_check_digit,
    levenshtein_distance,
    name_similarity_ratio,
    validate_pan_format,
    validate_verhoeff,
)
from app.modules.forensics.classifier import (
    DocumentFeatureReport,
    DocumentType,
    DynamicDocumentExtractor,
)
from app.modules.forensics.qr import (
    AadhaarSecureQRVerifier,
    create_signed_secure_qr_payload,
    generate_test_uidai_keypair,
)
from app.modules.forensics.schemas import (
    DocumentForensicAssessment,
    FieldContradictionReport,
    SecureQRVerificationResult,
)

from app.modules.forensics.face_index import (
    FaceDeduplicationIndex,
    create_face_reuse_edges,
)
from app.modules.forensics.contradiction import (
    ContradictionCheck,
    ContradictionReport,
    CrossSourceContradictionDetector,
)
from app.core.forensics import FaceMatch

__all__ = [
    "OCRExtractor",
    "FieldContradictionDetector",
    "validate_verhoeff",
    "compute_verhoeff_check_digit",
    "validate_pan_format",
    "levenshtein_distance",
    "name_similarity_ratio",
    "compare_dobs",
    "AadhaarSecureQRVerifier",
    "generate_test_uidai_keypair",
    "create_signed_secure_qr_payload",
    "FieldContradictionReport",
    "SecureQRVerificationResult",
    "DocumentForensicAssessment",
    "check_image_dimension_anomaly",
    "check_exif_metadata_anomaly",
    "check_jpeg_quality_factor_anomaly",
    "compute_error_level_analysis",
    "compute_fft_spectral_analysis",
    "compare_face_embeddings",
    "compute_face_embedding",
    "run_fast_plane_forensics",
    "run_slow_plane_forensics",
    "DynamicDocumentExtractor",
    "DocumentFeatureReport",
    "DocumentType",
    "FaceDeduplicationIndex",
    "FaceMatch",
    "create_face_reuse_edges",
    "CrossSourceContradictionDetector",
    "ContradictionReport",
    "ContradictionCheck",
]

