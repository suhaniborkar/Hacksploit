import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  CheckCircle2,
  Clock,
  ArrowRight,
  FileCheck,
  AlertTriangle,
  UserPlus,
  BarChart,
} from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable, type Column } from '../components/DataTable';
import { SecondaryButton } from '../components/SecondaryButton';
import { dashboardService } from '../services/dashboardService';
import type { Application, MetricCardData } from '../types/dashboard';

export function DashboardHome() {
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<MetricCardData[]>([]);
  const [recentApplications, setRecentApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [m, apps] = await Promise.all([
          dashboardService.getSummaryMetrics(),
          dashboardService.getApplications(),
        ]);
        setMetrics(m);
        // Show recent 5 applications
        setRecentApplications(apps.slice(0, 5));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const columns: Column<Application>[] = [
    {
      key: 'applicant',
      header: 'Applicant',
      render: (row) => (
        <div>
          <strong>{row.applicant.fullName}</strong>
          <div className="text-secondary" style={{ fontSize: '0.82rem' }}>
            {row.applicant.email}
          </div>
        </div>
      ),
    },
    {
      key: 'appId',
      header: 'Application ID',
      render: (row) => <span style={{ fontWeight: 600 }}>{row.appId}</span>,
    },
    {
      key: 'documentType',
      header: 'Document Type',
      render: (row) => (
        <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>
          {row.documentType.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'submittedAt',
      header: 'Submitted',
      render: (row) => (
        <span style={{ color: 'var(--dash-text-secondary)', fontSize: '0.88rem' }}>
          {new Date(row.submittedAt).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (row) => (
        <SecondaryButton
          style={{ minHeight: 34, padding: '0.35rem 0.85rem', fontSize: '0.85rem' }}
          onClick={() => navigate(`/applications/${row.id}`)}
        >
          View Details
        </SecondaryButton>
      ),
    },
  ];

  const metricIcons = [
    <Users key="1" size={24} />,
    <CheckCircle2 key="2" size={24} />,
    <Clock key="3" size={24} />,
  ];

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle="VeriYID AI-assisted identity verification and synthetic fraud screening."
        actions={
          <SecondaryButton
            icon={<ArrowRight size={16} />}
            onClick={() => navigate('/applications')}
          >
            All Applications
          </SecondaryButton>
        }
      />

      {/* 3 Summary Metric Cards */}
      <div className="dash-metric-grid">
        {metrics.map((m, idx) => (
          <MetricCard
            key={m.label}
            label={m.label}
            value={m.value}
            delta={m.delta}
            deltaLabel={m.deltaLabel}
            icon={metricIcons[idx % metricIcons.length]}
            onClick={() => navigate('/applications')}
          />
        ))}
      </div>

      {/* Recent Applications Panel */}
      <GlassPanel style={{ marginBottom: '1.75rem' }}>
        <div className="dash-section-heading">
          <span>Recent Applications</span>
          <button
            onClick={() => navigate('/applications')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--dash-text-primary)',
              fontSize: '0.88rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            View all ({recentApplications.length})
            <ArrowRight size={14} />
          </button>
        </div>

        <DataTable
          columns={columns}
          rows={recentApplications}
          rowKey={(r) => r.id}
          loading={loading}
          onRowClick={(r) => navigate(`/applications/${r.id}`)}
        />
      </GlassPanel>

      {/* Quick Actions Panel */}
      <GlassPanel>
        <div className="dash-section-heading">Quick Actions</div>
        <div className="dash-panel-body">
          <div className="dash-quick-actions">
            <div
              className="dash-quick-action-card"
              onClick={() => navigate('/applications')}
            >
              <FileCheck size={26} />
              <span>Review Queue</span>
            </div>

            <div
              className="dash-quick-action-card"
              onClick={() => navigate('/fraud-intelligence')}
            >
              <AlertTriangle size={26} />
              <span>Investigate Clusters</span>
            </div>

            <div
              className="dash-quick-action-card"
              onClick={() => navigate('/analytics')}
            >
              <BarChart size={26} />
              <span>View Analytics</span>
            </div>

            <div
              className="dash-quick-action-card"
              onClick={() => navigate('/users')}
            >
              <UserPlus size={26} />
              <span>Manage Team</span>
            </div>
          </div>
        </div>
      </GlassPanel>
    </>
  );
}

