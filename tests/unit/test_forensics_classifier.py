import io
import os
import pytest
from PIL import Image, ImageDraw

from app.modules.forensics.classifier import (
    DocumentType,
    DynamicDocumentExtractor,
)


def _make_card_image(title: str, id_text: str, name_text: str) -> bytes:
    img = Image.new("RGB", (856, 540), color=(250, 250, 252))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 856, 70], fill=(30, 45, 90))
    d.text((30, 25), title, fill=(255, 255, 255))
    d.text((50, 130), name_text, fill=(0, 0, 0))
    d.text((50, 190), id_text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


def test_regular_id_or_other_rejection():
    """Validates that non-statutory student/employee cards are rejected from KYC."""
    raw = _make_card_image(
        title="CAMPUS STUDENT ID CARD",
        id_text="Roll No: 2023CSB1042",
        name_text="Name: Rahul Verma",
    )
    extractor = DynamicDocumentExtractor()
    report = extractor.analyze_document(raw, filename="student_badge.jpg")
    assert report.document_type == DocumentType.REGULAR_ID_OR_OTHER
    assert report.is_statutory_kyc_document is False
    assert report.kyc_status == "REJECT"
    assert "Non-statutory" in report.kyc_summary


def test_real_aadhaar_card_extraction():
    """Validates extraction on real Aadhaar card if available on disk."""
    real_path = "/mnt/data/projects/modularMonolith/WhatsApp Image 2026-10-28 at 18.49.11.jpeg"
    if not os.path.exists(real_path):
        pytest.skip("Test image not present")

    with open(real_path, "rb") as f:
        raw = f.read()

    extractor = DynamicDocumentExtractor()
    report = extractor.analyze_document(raw, filename="WhatsApp Image 2026-10-28 at 18.49.11.jpeg")

    assert report.document_type == DocumentType.AADHAAR_CARD
    assert report.is_statutory_kyc_document is True
    assert report.id_number == "4597 1693 9274"
    assert report.id_format_valid is True
    assert report.checksum_or_rule_valid is True
    assert report.is_ai_generated is False
    assert report.kyc_status == "ACCEPTABLE"
    assert "Borkar" in (report.holder_name or "")


def test_ai_aadhaar_card_fraud_detection():
    """Validates rejection of AI generated Aadhaar failing Verhoeff checksum."""
    ai_path = "/mnt/data/projects/modularMonolith/ai_documents/Gemini_Generated_Image_krsb09krsb09krsb.png"
    if not os.path.exists(ai_path):
        pytest.skip("Test image not present")

    with open(ai_path, "rb") as f:
        raw = f.read()

    extractor = DynamicDocumentExtractor()
    report = extractor.analyze_document(raw, filename="Gemini_Generated_Image_krsb09krsb09krsb.png")

    assert report.document_type == DocumentType.AADHAAR_CARD
    assert report.id_number == "4521 7890 3214"
    assert report.checksum_or_rule_valid is False
    assert report.is_ai_generated is True
    assert report.kyc_status == "REJECT"
    assert any("Verhoeff" in r for r in report.ai_forensic_reasons)


def test_ai_pan_card_surname_and_typo_detection():
    """Validates rejection of AI PAN card with entity/surname mismatch and header typo."""
    pan_path = "/mnt/data/projects/modularMonolith/ai_documents/Gemini_Generated_Image_otq4fhotq4fhotq4.png"
    if not os.path.exists(pan_path):
        pytest.skip("Test image not present")

    with open(pan_path, "rb") as f:
        raw = f.read()

    extractor = DynamicDocumentExtractor()
    report = extractor.analyze_document(raw, filename="Gemini_Generated_Image_otq4fhotq4fhotq4.png")

    assert report.document_type == DocumentType.PAN_CARD
    assert report.id_number == "ABCDE1234F"
    assert report.checksum_or_rule_valid is False
    assert report.is_ai_generated is True
    assert report.kyc_status == "REJECT"


def test_ai_driving_licence_cross_document_hallucination():
    """Validates rejection of AI Driving Licence with hallucinated Aadhaar seal."""
    dl_path = "/mnt/data/projects/modularMonolith/ai_documents/Gemini_Generated_Image_4f86pb4f86pb4f86.png"
    if not os.path.exists(dl_path):
        pytest.skip("Test image not present")

    with open(dl_path, "rb") as f:
        raw = f.read()

    extractor = DynamicDocumentExtractor()
    report = extractor.analyze_document(raw, filename="Gemini_Generated_Image_4f86pb4f86pb4f86.png")

    assert report.document_type == DocumentType.DRIVING_LICENCE
    assert report.is_ai_generated is True
    assert report.kyc_status == "REJECT"
    assert any("Cross-document hallucination" in r for r in report.ai_forensic_reasons)
