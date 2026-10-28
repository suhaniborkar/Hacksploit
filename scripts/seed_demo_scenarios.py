"""
Seed Demo Scenarios Script for Project ARGUS.
Populates realistic multi-applicant graph scenarios:
1. Genuine Applicants (Verified, low risk, clean statutory IDs & biometric match)
2. AI Document Forgery Attacks (Rejected, C2PA GenAI provenance tags, checksum failure)
3. Coordinated Synthetic Identity Ring (Flagged, shared device & phone, ArcFace face reuse)

Usage:
    python3 scripts/seed_demo_scenarios.py
"""

import sys
import os
import uuid
from datetime import datetime, timezone, timedelta

# Ensure repo root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructure.database import SessionLocal, Base, engine
from app.core.security import hash_pii
from app.modules.identity.seed import seed_default_staff
from app.modules.kyc.models import KYCApplication
from app.modules.graph.models import ApplicantNode, ApplicantEdge, NodeType, EdgeType


def seed_demo_scenarios(db=None) -> dict:
    """
    Seeds idempotent demo scenarios into the database.
    Returns summary statistics of created applications and clusters.
    """
    close_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_db = True

    try:
        # 1. Ensure staff accounts exist
        seed_default_staff(db)

        # 2. Cleanup previous demo applications to ensure idempotency
        existing_apps = (
            db.query(KYCApplication)
            .filter(
                (KYCApplication.applicant_id.like("KYC-2026-100%"))
                | (KYCApplication.applicant_id.like("KYC-2026-200%"))
                | (KYCApplication.applicant_id.like("KYC-2026-300%"))
            )
            .all()
        )
        for app in existing_apps:
            # Delete associated nodes and edges
            db.query(ApplicantEdge).filter(
                (ApplicantEdge.source_hash == app.applicant_id)
                | (ApplicantEdge.target_hash == app.applicant_id)
            ).delete(synchronize_session=False)
            db.query(ApplicantNode).filter(
                ApplicantNode.applicant_id == app.applicant_id
            ).delete(synchronize_session=False)
            db.delete(app)
        db.commit()

        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # Scenario 1: Clean Genuine Applicants (Verified, low risk)
        # -------------------------------------------------------------
        clean_applicants_data = [
            {
                "app_id": "KYC-2026-1001",
                "name": "Aarav Sharma",
                "email": "aarav.sharma@example.com",
                "phone": "+919820111221",
                "dob": "1994-06-15",
                "id_type": "aadhaar",
                "id_num": "459716939274",
                "last4": "9274",
                "device": "device_fp_clean_aarav_safari_mac",
                "ip": "103.21.124.11",
                "city": "Mumbai",
                "state": "Maharashtra",
                "address": "402, Sea Green Apts, Worli Sea Face",
                "risk_score": 0.04,
                "status": "verified",
                "time_offset_hours": 12,
            },
            {
                "app_id": "KYC-2026-1002",
                "name": "Priya Patel",
                "email": "priya.patel@example.com",
                "phone": "+919820222332",
                "dob": "1997-11-20",
                "id_type": "pan",
                "id_num": "ABCDE1234F",
                "last4": "1234F",
                "device": "device_fp_clean_priya_chrome_win",
                "ip": "103.21.124.22",
                "city": "Ahmedabad",
                "state": "Gujarat",
                "address": "12, Shanti Kunj, Navrangpura",
                "risk_score": 0.06,
                "status": "verified",
                "time_offset_hours": 8,
            },
            {
                "app_id": "KYC-2026-1003",
                "name": "Rohan Deshmukh",
                "email": "rohan.deshmukh@example.com",
                "phone": "+919820333443",
                "dob": "1991-03-08",
                "id_type": "driving_licence",
                "id_num": "MH1220180012345",
                "last4": "2345",
                "device": "device_fp_clean_rohan_android_pixel",
                "ip": "103.21.124.33",
                "city": "Pune",
                "state": "Maharashtra",
                "address": "78, FC Road, Shivaji Nagar",
                "risk_score": 0.05,
                "status": "verified",
                "time_offset_hours": 4,
            },
        ]

        for item in clean_applicants_data:
            _create_application_with_graph(db, item, reasons=["CLEAN: Genuine statutory identity and passing biometric challenge."], is_synthetic=False, timestamp=now - timedelta(hours=item["time_offset_hours"]))

        # -------------------------------------------------------------
        # Scenario 2: AI Document Forgery Attacks (Immediate Hard Rejection)
        # -------------------------------------------------------------
        ai_forgery_data = [
            {
                "app_id": "KYC-2026-2001",
                "name": "Kunal Singhania",
                "email": "kunal.singh@syntheticmail.cc",
                "phone": "+919711888991",
                "dob": "1996-08-12",
                "id_type": "aadhaar",
                "id_num": "452178903214",
                "last4": "3214",
                "device": "device_fp_kunal_headless_chromium",
                "ip": "185.220.101.5",
                "city": "Delhi",
                "state": "Delhi",
                "address": "Flat 101, Connaught Place",
                "risk_score": 0.98,
                "status": "rejected",
                "reasons": [
                    "IMAGE_AI_SYNTHETIC: C2PA Provenance Manifest signed by Google Generative AI (Gemini/Imagen)",
                    "R5_INVALID_ID_CHECKSUM: Verhoeff D5 dihedral permutation check failed on 12-digit UIDAI number",
                    "Visual Pseudo-QR hallucination (zero decodable bytes)",
                ],
                "time_offset_hours": 6,
            },
            {
                "app_id": "KYC-2026-2002",
                "name": "Neha Malhotra",
                "email": "neha.m99@disposableinbox.org",
                "phone": "+919711999002",
                "dob": "1999-04-25",
                "id_type": "pan",
                "id_num": "XYZPK9876Q",
                "last4": "876Q",
                "device": "device_fp_neha_automated_script",
                "ip": "185.220.101.9",
                "city": "Gurgaon",
                "state": "Haryana",
                "address": "Tower 4, Cyber City",
                "risk_score": 0.94,
                "status": "rejected",
                "reasons": [
                    "R3_NAME_CONTRADICTION: 5th character of PAN does not match surname initial ('M')",
                    "IMAGE_AI_SYNTHETIC: 2D FFT spectral analysis detected periodic checkerboard GAN upsampling artifacts",
                ],
                "time_offset_hours": 2,
            },
        ]

        for item in ai_forgery_data:
            _create_application_with_graph(db, item, reasons=item["reasons"], is_synthetic=True, timestamp=now - timedelta(hours=item["time_offset_hours"]))

        # -------------------------------------------------------------
        # Scenario 3: Coordinated Synthetic Identity Ring (Unmasking the Ring)
        # 3 applicants sharing the exact same device fingerprint and phone number
        # with cross-application ArcFace face reuse detected
        # -------------------------------------------------------------
        shared_phone_raw = "+919876000111"
        shared_device_raw = "browser_canvas_fp_syndicate_ring_x7"

        ring_members_data = [
            {
                "app_id": "KYC-2026-3001",
                "name": "Vikram Joshi",
                "email": "vikram.joshi.ops@proton.me",
                "phone": shared_phone_raw,
                "dob": "1992-02-14",
                "id_type": "aadhaar",
                "id_num": "992144556611",
                "last4": "6611",
                "device": shared_device_raw,
                "ip": "198.51.100.42",
                "city": "Bengaluru",
                "state": "Karnataka",
                "address": "B-304, Indiranagar 100ft Road",
                "risk_score": 0.88,
                "status": "flagged",
                "time_offset_hours": 5,
            },
            {
                "app_id": "KYC-2026-3002",
                "name": "Rajesh Nair",
                "email": "rajesh.nair.cloud@proton.me",
                "phone": shared_phone_raw,
                "dob": "1990-09-30",
                "id_type": "aadhaar",
                "id_num": "992144556622",
                "last4": "6622",
                "device": shared_device_raw,
                "ip": "198.51.100.42",
                "city": "Bengaluru",
                "state": "Karnataka",
                "address": "B-304, Indiranagar 100ft Road",
                "risk_score": 0.89,
                "status": "flagged",
                "time_offset_hours": 3,
            },
            {
                "app_id": "KYC-2026-3003",
                "name": "Arjun Mehta",
                "email": "arjun.mehta.fin@proton.me",
                "phone": shared_phone_raw,
                "dob": "1995-12-05",
                "id_type": "pan",
                "id_num": "MEHTP4433K",
                "last4": "4433K",
                "device": shared_device_raw,
                "ip": "198.51.100.42",
                "city": "Bengaluru",
                "state": "Karnataka",
                "address": "B-304, Indiranagar 100ft Road",
                "risk_score": 0.91,
                "status": "flagged",
                "time_offset_hours": 1,
            },
        ]

        ring_reasons = [
            "R1_HIGH_PHONE_REUSE: Phone number reused across 3 distinct applicant identities",
            "R2_HIGH_DEVICE_REUSE: Device fingerprint shared with active synthetic identity cluster",
            "FACE_REUSE_DETECTED: Biometric ArcFace cosine distance 0.18 with previously indexed applicant",
        ]

        for item in ring_members_data:
            _create_application_with_graph(
                db, item, reasons=ring_reasons, is_synthetic=True, timestamp=now - timedelta(hours=item["time_offset_hours"])
            )

        # Cross-application Biometric Edge: Face Reuse between 3001 and 3003
        face_edge = ApplicantEdge(
            source_hash="KYC-2026-3001",
            target_hash="KYC-2026-3003",
            edge_type=EdgeType.FACE_REUSE_DETECTED.value,
        )
        db.add(face_edge)
        db.commit()

        total_apps = db.query(KYCApplication).count()
        total_nodes = db.query(ApplicantNode).count()
        total_edges = db.query(ApplicantEdge).count()

        summary = {
            "total_applications": total_apps,
            "total_graph_nodes": total_nodes,
            "total_graph_edges": total_edges,
            "clean_count": len(clean_applicants_data),
            "ai_forgery_count": len(ai_forgery_data),
            "ring_members_count": len(ring_members_data),
        }
        print("✅ Project ARGUS Demo Scenarios Seeded Successfully:")
        print(f"   • Total Applications: {total_apps}")
        print(f"   • Relational Graph Nodes: {total_nodes}")
        print(f"   • Graph Edges: {total_edges}")
        print(f"   • Clean Genuine Baseline: {len(clean_applicants_data)}")
        print(f"   • AI Forgery Attack Cases: {len(ai_forgery_data)}")
        print(f"   • Synthetic Fraud Ring Members: {len(ring_members_data)} (sharing phone, device, and ArcFace reuse)")

        return summary

    finally:
        if close_db:
            db.close()


def _create_application_with_graph(db, item: dict, reasons: list[str], is_synthetic: bool, timestamp: datetime):
    app_id = item["app_id"]
    phone_h = hash_pii(item["phone"], is_numeric_id=True)
    email_h = hash_pii(item["email"])
    device_h = hash_pii(item["device"])
    ip_h = hash_pii(item["ip"])
    identity_h = hash_pii(item["id_num"], is_numeric_id=True)

    risk_tier = "APPROVE" if item["risk_score"] < 0.20 else "REJECT"

    # Full forensic metadata payload for dossier view
    full_payload = {
        "personal": {
            "fullName": item["name"],
            "dateOfBirth": item["dob"],
            "nationality": "Indian",
        },
        "contact": {
            "email": item["email"],
            "mobile": item["phone"],
        },
        "address": {
            "residential": {
                "line1": item["address"],
                "city": item["city"],
                "stateRegion": item["state"],
                "country": "India",
            }
        },
        "device_fingerprint": item["device"],
    }

    meta = {
        "full_payload": full_payload,
        "ip_address": item["ip"],
        "history": [
            {
                "id": f"evt-{uuid.uuid4().hex[:8]}",
                "timestamp": timestamp.isoformat(),
                "action": "submitted",
                "actor": "applicant",
                "notes": f"Identity application submitted via web onboarding console from {item['city']}, India.",
            },
            {
                "id": f"evt-{uuid.uuid4().hex[:8]}",
                "timestamp": (timestamp + timedelta(seconds=1)).isoformat(),
                "action": "screened",
                "actor": "system_m0_rules",
                "notes": f"Automated M0 screening evaluated risk score: {item['risk_score']:.2f} ({risk_tier}).",
            },
        ],
    }

    app_record = KYCApplication(
        id=uuid.uuid4(),
        applicant_id=app_id,
        account_type="savings",
        id_type=item["id_type"],
        claimed_name=item["name"],
        claimed_dob=item["dob"],
        id_number_last4=item["last4"],
        identity_hash=identity_h,
        phone_hash=phone_h,
        email_hash=email_h,
        device_fingerprint_hash=device_h,
        ip_address_hash=ip_h,
        document_artifact_uri=f"artifacts_data/{app_id}_doc.jpg",
        selfie_artifact_uri=f"artifacts_data/{app_id}_selfie.jpg",
        document_mime_type="image/jpeg",
        selfie_mime_type="image/jpeg",
        status=item["status"],
        risk_tier=risk_tier,
        risk_score=item["risk_score"],
        reasons_json=reasons,
        metadata_json=meta,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(app_record)

    # Graph Node
    node = ApplicantNode(
        id=uuid.uuid4(),
        applicant_id=app_id,
        node_type=NodeType.APPLICANT.value,
        identity_hash=identity_h,
        phone_hash=phone_h,
        email_hash=email_h,
        device_fingerprint_hash=device_h,
        ip_address_hash=ip_h,
        status=item["status"],
        risk_score=item["risk_score"],
        is_fraud=is_synthetic,
        properties_json={"city": item["city"], "id_type": item["id_type"]},
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(node)

    # Graph Edges
    edges = [
        ApplicantEdge(source_hash=app_id, target_hash=identity_h, edge_type=EdgeType.HAS_IDENTITY.value, created_at=timestamp),
        ApplicantEdge(source_hash=app_id, target_hash=phone_h, edge_type=EdgeType.HAS_PHONE.value, created_at=timestamp),
        ApplicantEdge(source_hash=app_id, target_hash=email_h, edge_type=EdgeType.HAS_EMAIL.value, created_at=timestamp),
        ApplicantEdge(source_hash=app_id, target_hash=device_h, edge_type=EdgeType.HAS_DEVICE.value, created_at=timestamp),
        ApplicantEdge(source_hash=app_id, target_hash=ip_h, edge_type=EdgeType.HAS_IP.value, created_at=timestamp),
    ]
    for edge in edges:
        db.add(edge)


if __name__ == "__main__":
    seed_demo_scenarios()
