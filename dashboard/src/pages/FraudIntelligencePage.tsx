import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Network,
  Share2,
  ShieldAlert,
  Info,
  ExternalLink,
} from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { LoadingState } from '../components/LoadingState';
import { DataTable, type Column } from '../components/DataTable';
import { dashboardService } from '../services/dashboardService';
import type { SharedIdentifierCluster, FraudCluster } from '../types/dashboard';

interface GraphNode {
  id: string;
  type: 'hub' | 'applicant';
  subType?: string;
  label: string;
  sublabel?: string;
  x: number;
  y: number;
  risk?: string;
  applications?: string[];
  note?: string;
}

interface GraphEdge {
  fromId: string;
  toId: string;
  type: 'has_identifier' | 'face_reuse';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export function FraudIntelligencePage() {
  const navigate = useNavigate();
  const [clusters, setClusters] = useState<{ shared: SharedIdentifierCluster[]; rings: FraudCluster[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await dashboardService.getFraudClusters();
        setClusters(res);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const graphData = useMemo(() => {
    if (!clusters) return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };

    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];
    const sharedList = clusters.shared;
    const ringList = clusters.rings;

    const applicantMap = new Map<string, { rings: string[]; hubs: string[]; risk: string }>();

    ringList.forEach((r) => {
      r.applicationIds.forEach((aid) => {
        if (!applicantMap.has(aid)) {
          applicantMap.set(aid, { rings: [r.clusterLabel], hubs: [], risk: r.riskLevel });
        } else {
          applicantMap.get(aid)!.rings.push(r.clusterLabel);
        }
      });
    });

    sharedList.forEach((s) => {
      s.applicationIds.forEach((aid) => {
        if (!applicantMap.has(aid)) {
          applicantMap.set(aid, { rings: [], hubs: [s.identifierType], risk: 'high' });
        } else {
          applicantMap.get(aid)!.hubs.push(s.identifierType);
        }
      });
    });

    const svgWidth = 860;
    const svgHeight = 380;
    const hubCount = Math.max(1, sharedList.length);
    const hubSpacing = svgWidth / (hubCount + 1);
    const hubPositions = new Map<string, { x: number; y: number }>();

    sharedList.forEach((hub, idx) => {
      const hx = Math.round(hubSpacing * (idx + 1));
      const hy = Math.round(svgHeight / 2);
      hubPositions.set(hub.id, { x: hx, y: hy });

      nodes.push({
        id: hub.id,
        type: 'hub',
        subType: hub.identifierType,
        label: `Shared ${hub.identifierType.toUpperCase()}`,
        sublabel: hub.identifierValue,
        x: hx,
        y: hy,
        applications: hub.applicationIds,
        note: hub.note,
      });
    });

    const allApplicants = Array.from(applicantMap.keys());
    const totalApplicants = allApplicants.length;

    allApplicants.forEach((aid, idx) => {
      const connectedHubs = sharedList.filter((s) => s.applicationIds.includes(aid));
      let ax = 0;
      let ay = 0;

      if (connectedHubs.length === 1) {
        const hubPos = hubPositions.get(connectedHubs[0].id) || { x: 430, y: 190 };
        const angle = (2 * Math.PI / Math.max(1, connectedHubs[0].applicationIds.length)) * idx - Math.PI / 2;
        const dist = 120;
        ax = Math.max(65, Math.min(svgWidth - 65, hubPos.x + Math.cos(angle) * dist));
        ay = Math.max(50, Math.min(svgHeight - 50, hubPos.y + Math.sin(angle) * dist));
      } else if (connectedHubs.length > 1) {
        const sumX = connectedHubs.reduce((acc, h) => acc + (hubPositions.get(h.id)?.x || 430), 0);
        const sumY = connectedHubs.reduce((acc, h) => acc + (hubPositions.get(h.id)?.y || 190), 0);
        ax = sumX / connectedHubs.length;
        ay = (sumY / connectedHubs.length) + (idx % 2 === 0 ? -110 : 110);
      } else {
        const angle = (2 * Math.PI / Math.max(1, totalApplicants)) * idx;
        ax = 430 + Math.cos(angle) * 170;
        ay = 190 + Math.sin(angle) * 125;
      }

      const info = applicantMap.get(aid);
      nodes.push({
        id: aid,
        type: 'applicant',
        label: aid,
        sublabel: info?.rings.join(', ') || 'Correlated Identity Record',
        x: Math.round(ax),
        y: Math.round(ay),
        risk: info?.risk || 'critical',
      });

      connectedHubs.forEach((hub) => {
        const hPos = hubPositions.get(hub.id);
        if (hPos) {
          edges.push({
            fromId: hub.id,
            toId: aid,
            type: 'has_identifier',
            x1: hPos.x,
            y1: hPos.y,
            x2: Math.round(ax),
            y2: Math.round(ay),
          });
        }
      });
    });

    // Face Reuse Edges
    ringList.forEach((r) => {
      const isFaceReuse = r.sharedIndicators.some((sig) =>
        sig.toLowerCase().includes('face') || sig.toLowerCase().includes('biometric')
      );
      if (isFaceReuse && r.applicationIds.length >= 2) {
        for (let i = 0; i < r.applicationIds.length - 1; i++) {
          const a1 = nodes.find((n) => n.id === r.applicationIds[i]);
          const a2 = nodes.find((n) => n.id === r.applicationIds[i + 1]);
          if (a1 && a2) {
            edges.push({
              fromId: a1.id,
              toId: a2.id,
              type: 'face_reuse',
              x1: a1.x,
              y1: a1.y,
              x2: a2.x,
              y2: a2.y,
            });
          }
        }
      }
    });

    return { nodes, edges };
  }, [clusters]);

  const selectedEntity = useMemo(() => {
    return graphData.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [graphData.nodes, selectedNodeId]);

  if (loading || !clusters) {
    return <LoadingState message="Loading fraud intelligence graph and cluster models..." />;
  }

  const sharedColumns: Column<SharedIdentifierCluster>[] = [
    {
      key: 'identifierType',
      header: 'Identifier Type',
      render: (row) => (
        <span style={{ fontWeight: 700, textTransform: 'capitalize' }}>
          {row.identifierType}
        </span>
      ),
    },
    {
      key: 'identifierValue',
      header: 'Pseudonymized Key / Hash',
      render: (row) => (
        <code style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--dash-text-primary)' }}>
          {row.identifierValue}
        </code>
      ),
    },
    {
      key: 'applicationIds',
      header: 'Associated Applications',
      render: (row) => (
        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
          {row.applicationIds.map((id) => (
            <button
              key={id}
              onClick={() => navigate(`/applications`)}
              style={{
                fontSize: '0.8rem',
                padding: '0.15rem 0.5rem',
                borderRadius: '4px',
                border: '1px solid rgba(18,63,61,0.2)',
                background: 'rgba(255,255,255,0.7)',
                color: 'var(--dash-text-primary)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {id}
            </button>
          ))}
        </div>
      ),
    },
    {
      key: 'activity',
      header: 'Observed Range',
      render: (row) => (
        <span style={{ fontSize: '0.85rem', color: 'var(--dash-text-secondary)' }}>
          {row.firstSeen} → {row.lastSeen}
        </span>
      ),
    },
    {
      key: 'note',
      header: 'Intelligence Finding',
      render: (row) => (
        <span style={{ fontSize: '0.88rem', color: 'var(--dash-text-secondary)' }}>
          {row.note}
        </span>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Fraud Intelligence & Syndicate Detection"
        subtitle="Graph-based cross-application correlation, repeated identifier detection, and synthetic cluster screening."
      />

      {/* Critical Methodological Notice */}
      <div className="dash-fraud-banner">
        <Info size={20} />
        <div>
          <strong>Evidence vs Correlation Notice:</strong> An observed shared identifier (such as a device or subnet) indicates an identity relation, not definitive fraud. Full confirmation requires forensic proof of tampering or statutory credential invalidity.
        </div>
      </div>

      {/* Interactive Entity Relationship Graph Visualizer */}
      <GlassPanel style={{ marginBottom: '1.75rem' }}>
        <div className="dash-section-heading">
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Network size={18} /> Identity Relational Graph & Multi-Hop Entity Visualizer
          </span>
          <span style={{ fontSize: '0.85rem', color: 'var(--dash-text-muted)', fontWeight: 600 }}>
            Dynamic Ego-Projections Derived from Active Database Clusters
          </span>
        </div>

        <div className="dash-panel-body">
          <div className="dash-graph-container" style={{ position: 'relative', overflowX: 'auto', background: 'rgba(18, 63, 61, 0.03)', borderRadius: '10px', padding: '1rem' }}>
            <svg
              className="dash-graph-svg"
              viewBox="0 0 860 380"
              style={{ width: '100%', minWidth: '760px', height: '380px' }}
              role="img"
              aria-label="Dynamic identity relational graph network"
            >
              {/* Definitions for arrowheads and markers */}
              <defs>
                <marker id="arrow" viewBox="0 0 10 10" refX="16" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(18,63,61,0.4)" />
                </marker>
              </defs>

              {/* Render Graph Edges */}
              {graphData.edges.map((edge, idx) => (
                <g key={`edge-${idx}`}>
                  <line
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    stroke={edge.type === 'face_reuse' ? '#dc2626' : 'rgba(18,63,61,0.3)'}
                    strokeWidth={edge.type === 'face_reuse' ? 2.5 : 1.8}
                    strokeDasharray={edge.type === 'face_reuse' ? '6 3' : '4 4'}
                  />
                  {edge.type === 'face_reuse' && (
                    <g transform={`translate(${(edge.x1 + edge.x2) / 2}, ${(edge.y1 + edge.y2) / 2})`}>
                      <rect x="-65" y="-10" width="130" height="20" rx="4" fill="#fee2e2" stroke="#dc2626" strokeWidth="1" />
                      <text textAnchor="middle" dy="4" fill="#b91c1c" fontSize="9" fontWeight="800">
                        FACE_REUSE_DETECTED
                      </text>
                    </g>
                  )}
                </g>
              ))}

              {/* Render Graph Nodes */}
              {graphData.nodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                if (node.type === 'hub') {
                  return (
                    <g
                      key={node.id}
                      className="dash-graph-node"
                      transform={`translate(${node.x}, ${node.y})`}
                      onClick={() => setSelectedNodeId(node.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <circle
                        r={isSelected ? 38 : 34}
                        fill="var(--dash-accent)"
                        stroke={isSelected ? '#ffffff' : 'rgba(18,63,61,0.3)'}
                        strokeWidth={isSelected ? 3 : 1}
                      />
                      <circle r={isSelected ? 46 : 42} fill="none" stroke="rgba(18,63,61,0.2)" strokeWidth="1.5" strokeDasharray="3 3" />
                      <text textAnchor="middle" dy="-4" fill="#ffffff" fontSize="10" fontWeight="800">
                        {node.subType === 'device' ? 'SHARED DEVICE' : node.subType === 'phone' ? 'SHARED PHONE' : 'SHARED HUB'}
                      </text>
                      <text textAnchor="middle" dy="12" fill="rgba(255,255,255,0.85)" fontSize="8" fontWeight="600">
                        {node.applications?.length || 0} Linked IDs
                      </text>
                    </g>
                  );
                }

                // Applicant Node
                const isCritical = node.risk === 'critical' || node.risk === 'high';
                const nodeColor = isCritical ? 'rgba(239, 68, 68, 0.9)' : 'rgba(245, 158, 11, 0.9)';
                return (
                  <g
                    key={node.id}
                    className="dash-graph-node"
                    transform={`translate(${node.x}, ${node.y})`}
                    onClick={() => setSelectedNodeId(node.id)}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      r={isSelected ? 28 : 24}
                      fill={nodeColor}
                      stroke={isSelected ? '#111827' : '#ffffff'}
                      strokeWidth={isSelected ? 3 : 1.5}
                    />
                    <text textAnchor="middle" dy="4" fill="#ffffff" fontSize="9" fontWeight="800">
                      {node.label.replace('KYC-2026-', '')}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Dynamic Inspector Panel for Selected Graph Entity */}
          {selectedEntity ? (
            <div
              style={{
                marginTop: '1rem',
                padding: '1.1rem 1.4rem',
                background: 'rgba(255, 255, 255, 0.8)',
                borderRadius: '10px',
                border: '1px solid rgba(18, 63, 61, 0.25)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 800, textTransform: 'uppercase', padding: '0.15rem 0.5rem', borderRadius: '4px', background: selectedEntity.type === 'hub' ? 'var(--dash-accent)' : '#fee2e2', color: selectedEntity.type === 'hub' ? '#ffffff' : '#b91c1c' }}>
                    {selectedEntity.type === 'hub' ? 'Shared Identifier Hub' : 'Applicant Node'}
                  </span>
                  <strong style={{ fontSize: '1.05rem', color: 'var(--dash-text-primary)' }}>
                    {selectedEntity.label}
                  </strong>
                </div>
                {selectedEntity.sublabel && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--dash-text-secondary)', marginTop: '0.35rem' }}>
                    {selectedEntity.sublabel}
                  </div>
                )}
                {selectedEntity.note && (
                  <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.25rem', maxWidth: '620px' }}>
                    {selectedEntity.note}
                  </div>
                )}
                {selectedEntity.applications && selectedEntity.applications.length > 0 && (
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--dash-text-muted)' }}>Connected Applications:</span>
                    {selectedEntity.applications.map((aid) => (
                      <button
                        key={aid}
                        onClick={() => navigate(`/applications/${aid}`)}
                        style={{
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          padding: '0.15rem 0.5rem',
                          borderRadius: '4px',
                          border: '1px solid rgba(18,63,61,0.2)',
                          background: 'rgba(255,255,255,0.9)',
                          cursor: 'pointer',
                        }}
                      >
                        {aid}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {selectedEntity.type === 'applicant' && (
                <button
                  className="dash-btn-primary"
                  onClick={() => navigate(`/applications/${selectedEntity.label}`)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.55rem 1.1rem', fontSize: '0.9rem' }}
                >
                  <ExternalLink size={15} /> Open Forensic Dossier
                </button>
              )}
            </div>
          ) : (
            <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--dash-text-muted)', textAlign: 'center' }}>
              💡 Click on any node or shared hub above to inspect connected entities, correlated rings, and open forensic dossiers.
            </div>
          )}
        </div>
      </GlassPanel>

      {/* Suspicious Syndicate Clusters */}
      <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '1rem', color: 'var(--dash-text-primary)' }}>
        Identified Fraud Clusters & Syndicate Rings
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.25rem', marginBottom: '2rem' }}>
        {clusters.rings.map((ring) => (
          <GlassPanel key={ring.id}>
            <div className="dash-section-heading">
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <ShieldAlert size={18} />
                <span>{ring.clusterLabel}</span>
              </span>
              <span
                style={{
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  padding: '0.2rem 0.55rem',
                  borderRadius: '4px',
                  background: 'rgba(254, 226, 226, 0.9)',
                }}
              >
                {ring.riskLevel}
              </span>
            </div>
            <div className="dash-panel-body">
              <p style={{ fontSize: '0.92rem', color: 'var(--dash-text-secondary)', marginBottom: '1rem' }}>
                {ring.note}
              </p>

              <div style={{ marginBottom: '1rem' }}>
                <span className="dash-detail-label">Shared Cluster Signals:</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.35rem' }}>
                  {ring.sharedIndicators.map((sig, i) => (
                    <span
                      key={i}
                      style={{
                        fontSize: '0.82rem',
                        padding: '0.2rem 0.6rem',
                        borderRadius: '4px',
                        background: 'rgba(255,255,255,0.6)',
                        border: '1px solid rgba(0,0,0,0.08)',
                        fontWeight: 600,
                      }}
                    >
                      {sig}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="dash-detail-label">Correlated Applications ({ring.applicationIds.length}):</span>
                <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.35rem' }}>
                  {ring.applicationIds.map((id) => (
                    <button
                      key={id}
                      onClick={() => navigate('/applications')}
                      style={{
                        padding: '0.25rem 0.6rem',
                        borderRadius: '4px',
                        border: '1px solid rgba(18,63,61,0.25)',
                        background: 'var(--dash-accent-light)',
                        color: 'var(--dash-text-primary)',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                      }}
                    >
                      {id}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </GlassPanel>
        ))}
      </div>

      {/* Shared Identifiers Table */}
      <GlassPanel>
        <div className="dash-section-heading">
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Share2 size={18} /> Cross-Application Shared Identifiers
          </span>
        </div>

        <DataTable
          columns={sharedColumns}
          rows={clusters.shared}
          rowKey={(r) => r.id}
        />
      </GlassPanel>
    </>
  );
}
