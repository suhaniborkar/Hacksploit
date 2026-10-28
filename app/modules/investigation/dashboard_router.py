from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.modules.identity.auth import require_staff
from app.modules.identity.models import User
from app.modules.investigation.schemas import (
    AnalyticsSeriesSchema,
    ApplicationSchema,
    DecisionRequest,
    FraudClustersResponseSchema,
    MetricCardSchema,
)
from app.modules.investigation.service import investigation_service

router = APIRouter(tags=["Investigation & Dashboard"])


@router.get("/dashboard/metrics", response_model=list[MetricCardSchema])
def get_dashboard_summary_metrics(
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Returns dynamic summary metric cards computed over live KYC applications,
    including total counts, clean pass rates, review backlogs, and fraud flags.
    """
    investigation_service.seed_demo_applications_if_needed(db)
    return investigation_service.get_summary_metrics(db)


@router.get("/dashboard/applications", response_model=list[ApplicationSchema])
def get_dashboard_applications(
    status: str | None = Query(default=None, description="Filter by status: verified, pending, flagged, review_required"),
    search: str | None = Query(default=None, description="Search query by name, ID, or document number"),
    doc_type: str | None = Query(default=None, description="Filter by document type: passport, national_id, drivers_license"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Returns filtered and paginated applications matching the dashboard Application schema.
    """
    investigation_service.seed_demo_applications_if_needed(db)
    return investigation_service.get_applications(
        db=db,
        status=status,
        search=search,
        doc_type=doc_type,
        skip=skip,
        limit=limit,
    )


@router.get("/dashboard/applications/{app_id}", response_model=ApplicationSchema)
def get_dashboard_application_detail(
    app_id: str,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Returns the full forensic dossier for a single KYC application.
    Accepts either the UUID primary key or the human-readable applicant_id (e.g. KYC-2026-XXXXX).
    """
    investigation_service.seed_demo_applications_if_needed(db)
    result = investigation_service.get_application_by_id(db, app_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return result


@router.post("/dashboard/applications/{app_id}/decision", response_model=ApplicationSchema)
def post_application_decision(
    app_id: str,
    body: DecisionRequest,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Records a compliance officer adjudication decision for a KYC case.

    Updates the application status and appends a timestamped entry to the
    embedded audit trail visible on the Audit Trail tab.
    Allowed statuses: verified, pending, flagged, review_required.
    """
    actor_label = f"{user.name or user.email} ({user.role})"
    try:
        result = investigation_service.apply_decision(
            db=db,
            app_id=app_id,
            new_status=body.status,
            actor=actor_label,
            note=body.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail=f"Application '{app_id}' not found.")
    return result


@router.get("/dashboard/analytics", response_model=AnalyticsSeriesSchema)
def get_dashboard_analytics(
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Returns time-series throughput, outcome ratios, and credential format distributions.
    """
    investigation_service.seed_demo_applications_if_needed(db)
    return investigation_service.get_analytics(db)


@router.get("/dashboard/clusters", response_model=FraudClustersResponseSchema)
def get_fraud_clusters(
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Returns shared-identifier clusters (repeated phone/email/device) and fraud ring
    groupings derived from the identity graph, keyed by Union-Find component membership.
    """
    investigation_service.seed_demo_applications_if_needed(db)
    return investigation_service.get_fraud_clusters(db)
