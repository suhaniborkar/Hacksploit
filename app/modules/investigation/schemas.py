from typing import Any
from pydantic import BaseModel, Field


class MetricCardSchema(BaseModel):
    label: str
    value: str | int
    delta: str | None = None
    deltaLabel: str | None = None
    iconName: str | None = None


class ChartDataPointSchema(BaseModel):
    label: str
    value: int


class ChartDataPointColoredSchema(BaseModel):
    label: str
    value: int
    color: str


class AnalyticsSeriesSchema(BaseModel):
    volumeOverTime: list[ChartDataPointSchema]
    outcomeDistribution: list[ChartDataPointColoredSchema]
    byDocumentType: list[ChartDataPointSchema]
    fraudFlagsOverTime: list[ChartDataPointSchema]


class ApplicantSchema(BaseModel):
    id: str
    appId: str
    fullName: str
    email: str
    phone: str
    dateOfBirth: str
    nationality: str
    address: str
    city: str
    country: str
    deviceFingerprint: str | None = None
    ipAddress: str | None = None


class DocumentSchema(BaseModel):
    type: str
    documentNumber: str
    issuingCountry: str
    issueDate: str
    expiryDate: str
    verified: bool
    extractedData: dict[str, Any] | None = None
    imageUrl: str | None = None
    backImageUrl: str | None = None
    forensicReport: dict[str, Any] | None = None


class BiometricDataSchema(BaseModel):
    selfieUrl: str | None = None
    livenessScore: float
    faceMatchScore: float
    antiSpoofScore: float
    passed: bool
    tamperingStatus: str | None = None


class RiskIndicatorSchema(BaseModel):
    code: str
    label: str
    severity: str
    description: str


class MismatchSchema(BaseModel):
    field: str
    documentValue: str
    declaredValue: str


class RiskAssessmentSchema(BaseModel):
    score: int
    level: str
    indicators: list[RiskIndicatorSchema] = Field(default_factory=list)
    mismatches: list[MismatchSchema] = Field(default_factory=list)
    sharedIdentifiers: list[str] = Field(default_factory=list)


class HistoryEventSchema(BaseModel):
    timestamp: str
    action: str
    actor: str
    note: str | None = None


class ApplicationSchema(BaseModel):
    id: str
    appId: str
    applicant: ApplicantSchema
    status: str
    documentType: str
    document: DocumentSchema
    biometric: BiometricDataSchema
    risk: RiskAssessmentSchema
    history: list[HistoryEventSchema] = Field(default_factory=list)
    submittedAt: str
    updatedAt: str


class DecisionRequest(BaseModel):
    """Payload for a case adjudication decision made by a staff member."""

    status: str
    note: str | None = None


class SharedIdentifierClusterSchema(BaseModel):
    """A set of applications sharing a pseudonymized identifier (phone, email, device)."""

    id: str
    identifierType: str
    identifierValue: str
    applicationIds: list[str]
    firstSeen: str
    lastSeen: str
    note: str


class FraudClusterSchema(BaseModel):
    """A synthetic fraud ring cluster grouping correlated high-risk applications."""

    id: str
    clusterLabel: str
    applicationIds: list[str]
    sharedIndicators: list[str]
    riskLevel: str
    note: str


class FraudClustersResponseSchema(BaseModel):
    shared: list[SharedIdentifierClusterSchema]
    rings: list[FraudClusterSchema]
