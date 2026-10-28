#!/usr/bin/env python3
"""
CLI Database Inspector for Project ARGUS.

Inspects all tables, counts, sample nodes, and relational identity graph edges.
Can also seed realistic sample KYC applications and fraud rings.

Usage:
    python3 scripts/inspect_db.py
    python3 scripts/inspect_db.py --seed
"""

from __future__ import annotations

import argparse

from sqlalchemy import func

from app.infrastructure.database import Base, SessionLocal, engine
from app.modules.identity.models import User, AuthSession, APIKey
from app.modules.kyc.models import KYCApplication
from app.modules.graph.models import ApplicantNode, ApplicantEdge, EdgeType, NodeType
from app.infrastructure.jobs.models import Job
from app.core.security import hash_pii


def init_schema() -> None:
    """Ensures all model tables are created in the database."""
    Base.metadata.create_all(bind=engine)


def inspect_database() -> None:
    """Displays tables, row counts, and sample records."""
    init_schema()

    print("\n" + "═" * 70)
    print("🗄️  PROJECT ARGUS — DATABASE INSPECTOR")
    print(f"   Connection URL: {engine.url}")
    print("═" * 70)

    with SessionLocal() as db:
        print("\n📊 TABLE SUMMARY & ROW COUNTS:")
        print(f"  {'Table Name':<28} {'Row Count':<12}")
        print("  " + "─" * 40)

        models = [
            ("applicant_nodes", ApplicantNode),
            ("applicant_edges", ApplicantEdge),
            ("kyc_applications", KYCApplication),
            ("users", User),
            ("jobs", Job),
            ("auth_sessions", AuthSession),
            ("api_keys", APIKey),
        ]

        for tbl_name, model in models:
            count = db.query(func.count()).select_from(model).scalar() or 0
            print(f"  {tbl_name:<28} {count:<12}")

        # Show Sample Applicant Nodes
        nodes = db.query(ApplicantNode).order_by(ApplicantNode.created_at.desc()).limit(5).all()
        print("\n🪪 RECENT APPLICANT NODES (Top 5):")
        if not nodes:
            print("  (No applicant nodes found. Run with `--seed` to populate sample data.)")
        else:
            print(f"  {'Applicant ID':<18} {'Status':<12} {'Risk Score':<12} {'Phone Hash (12 chars)':<24}")
            print("  " + "─" * 68)
            for n in nodes:
                p_hash = (n.phone_hash[:12] + "...") if n.phone_hash else "None"
                r_score = f"{n.risk_score:.3f}" if n.risk_score is not None else "None"
                print(f"  {n.applicant_id:<18} {n.status:<12} {r_score:<12} {p_hash:<24}")

        # Show Sample Graph Edges
        edges = db.query(ApplicantEdge).order_by(ApplicantEdge.created_at.desc()).limit(10).all()
        print("\n🕸️  RELATIONAL GRAPH EDGES (Top 10):")
        if not edges:
            print("  (No graph edges found. Run with `--seed` to populate sample data.)")
        else:
            print(f"  {'Source (10 chars)':<14} {'Edge Type':<24} {'Target (10 chars)':<14} {'Weight':<8}")
            print("  " + "─" * 64)
            for e in edges:
                s_h = e.source_hash[:10] + ".."
                t_h = e.target_hash[:10] + ".."
                print(f"  {s_h:<14} {e.edge_type:<24} {t_h:<14} {e.weight:<8.2f}")

    print("\n" + "═" * 70 + "\n")


def seed_sample_data() -> None:
    """Seeds realistic clean applicants and a synthetic fraud ring into the database."""
    init_schema()
    with SessionLocal() as db:
        print("\n🌱 Seeding realistic test KYC applications and synthetic fraud ring...")

        # 1. Clean Applicant
        clean_id = "app_clean_901"
        clean_phone = "+919876543210"
        clean_email = "vikram.mehta@example.com"
        clean_dev = "dev_iphone15_clean_001"
        clean_aadhaar = "459716939274"

        clean_node = ApplicantNode(
            applicant_id=clean_id,
            node_type=NodeType.APPLICANT.value,
            phone_hash=hash_pii(clean_phone, "phone"),
            email_hash=hash_pii(clean_email, "email"),
            device_fingerprint_hash=hash_pii(clean_dev, "device"),
            identity_hash=hash_pii(clean_aadhaar, "identity"),
            status="approved",
            risk_score=0.08,
            is_fraud=False,
            properties_json={"name": "Vikram Mehta", "state": "MH"},
        )
        db.merge(clean_node)

        # 2. Synthetic Fraud Ring: 4 applicants sharing 1 burner phone, 1 emulator, and face reuse
        ring_phone = "+919999988888"
        ring_phone_hash = hash_pii(ring_phone, "phone")
        ring_dev = "emulator_nox_shared_888"
        ring_dev_hash = hash_pii(ring_dev, "device")

        ring_members = [
            ("app_ring_001", "Sunil Verma", False, 0.45),
            ("app_ring_002", "Rajesh Sharma", False, 0.65),
            ("app_ring_003", "Amit Patel", True, 0.95),  # Confirmed fraud anchor
            ("app_ring_004", "Deepak Gupta", False, 0.70),
        ]

        for app_id, name, is_fraud, risk in ring_members:
            mem_node = ApplicantNode(
                applicant_id=app_id,
                node_type=NodeType.APPLICANT.value,
                phone_hash=ring_phone_hash,
                email_hash=hash_pii(f"{app_id}@disposable.xyz", "email"),
                device_fingerprint_hash=ring_dev_hash,
                identity_hash=hash_pii(f"aadhaar_{app_id}", "identity"),
                status="rejected" if is_fraud or risk >= 0.75 else "review",
                risk_score=risk,
                is_fraud=is_fraud,
                properties_json={"name": name, "synthetic_ring": "emulator_jamtara_01"},
            )
            db.merge(mem_node)

            # Edge to shared phone
            e_phone = ApplicantEdge(
                source_hash=app_id,
                target_hash=ring_phone_hash,
                edge_type=EdgeType.SHARED_PHONE.value,
                source_type=NodeType.APPLICANT.value,
                target_type="phone",
                weight=1.0,
                properties_json={"shared_count": 4},
            )
            db.merge(e_phone)

            # Edge to shared device
            e_dev = ApplicantEdge(
                source_hash=app_id,
                target_hash=ring_dev_hash,
                edge_type=EdgeType.SHARED_DEVICE.value,
                source_type=NodeType.APPLICANT.value,
                target_type="device",
                weight=1.0,
                properties_json={"shared_count": 4},
            )
            db.merge(e_dev)

        # Cross-identity Face Reuse Edge between ring_001 and ring_004
        face_reuse_edge = ApplicantEdge(
            source_hash="app_ring_001",
            target_hash="app_ring_004",
            edge_type=EdgeType.FACE_REUSE_DETECTED.value,
            source_type=NodeType.APPLICANT.value,
            target_type=NodeType.APPLICANT.value,
            weight=0.91,
            properties_json={"cosine_similarity": 0.91, "cosine_distance": 0.09, "reason": "same_face_multiple_aadhaar"},
        )
        db.merge(face_reuse_edge)

        db.commit()
        print("✅ Seed complete! 1 clean applicant + 4 synthetic ring members + graph edges created.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or seed the ARGUS database.")
    parser.add_argument("--seed", action="store_true", help="Seed sample KYC applications and fraud ring.")
    args = parser.parse_args()

    if args.seed:
        seed_sample_data()

    inspect_database()


if __name__ == "__main__":
    main()
