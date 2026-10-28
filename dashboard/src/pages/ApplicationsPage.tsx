import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, Download } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { SearchBar } from '../components/SearchBar';
import { FilterBar } from '../components/FilterBar';
import { DateRangePicker } from '../components/DateRangePicker';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable, type Column } from '../components/DataTable';
import { TablePagination } from '../components/TablePagination';
import { SecondaryButton } from '../components/SecondaryButton';
import { EmptyState } from '../components/EmptyState';
import { dashboardService } from '../services/dashboardService';
import type { Application, ApplicationStatus, DocumentType } from '../types/dashboard';

const PAGE_SIZE = 5;

export function ApplicationsPage() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);

  // Filters state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [docFilter, setDocFilter] = useState<string>('all');
  const [dateRange, setDateRange] = useState({ startDate: '', endDate: '' });
  const [page, setPage] = useState(1);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const data = await dashboardService.getApplications();
        setApplications(data);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const hasActiveFilters = search !== '' || statusFilter !== 'all' || docFilter !== 'all' || dateRange.startDate !== '' || dateRange.endDate !== '';

  const handleResetFilters = () => {
    setSearch('');
    setStatusFilter('all');
    setDocFilter('all');
    setDateRange({ startDate: '', endDate: '' });
    setPage(1);
  };

  const filtered = useMemo(() => {
    return applications.filter((app) => {
      // Search match
      if (search) {
        const query = search.toLowerCase();
        const matchName = app.applicant.fullName.toLowerCase().includes(query);
        const matchEmail = app.applicant.email.toLowerCase().includes(query);
        const matchPhone = app.applicant.phone.toLowerCase().includes(query);
        const matchAppId = app.appId.toLowerCase().includes(query);
        const matchDocNo = app.document.documentNumber.toLowerCase().includes(query);
        if (!matchName && !matchEmail && !matchPhone && !matchAppId && !matchDocNo) {
          return false;
        }
      }

      // Status filter
      if (statusFilter !== 'all' && app.status !== statusFilter) {
        return false;
      }

      // Document filter
      if (docFilter !== 'all' && app.documentType !== docFilter) {
        return false;
      }

      // Date range filter
      if (dateRange.startDate) {
        const appDate = new Date(app.submittedAt).toISOString().slice(0, 10);
        if (appDate < dateRange.startDate) return false;
      }
      if (dateRange.endDate) {
        const appDate = new Date(app.submittedAt).toISOString().slice(0, 10);
        if (appDate > dateRange.endDate) return false;
      }

      return true;
    });
  }, [applications, search, statusFilter, docFilter, dateRange]);

  // Paginated rows
  const paginatedRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);

  const columns: Column<Application>[] = [
    {
      key: 'applicant',
      header: 'Applicant Details',
      render: (row) => (
        <div>
          <strong style={{ fontSize: '1rem' }}>{row.applicant.fullName}</strong>
          <div className="text-secondary" style={{ fontSize: '0.82rem' }}>
            {row.applicant.email} • {row.applicant.nationality}
          </div>
        </div>
      ),
    },
    {
      key: 'appId',
      header: 'Application ID',
      render: (row) => <span style={{ fontWeight: 700 }}>{row.appId}</span>,
    },
    {
      key: 'document',
      header: 'Document & ID',
      render: (row) => (
        <div>
          <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>
            {row.documentType.replace('_', ' ')}
          </span>
          <div className="text-secondary" style={{ fontSize: '0.82rem' }}>
            {row.document.documentNumber}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'KYC Status',
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: 'riskScore',
      header: 'Fraud Risk Tier',
      render: (row) => (
        <span
          style={{
            fontWeight: 700,
            textTransform: 'uppercase',
            fontSize: '0.82rem',
            padding: '0.2rem 0.6rem',
            borderRadius: '4px',
            background:
              row.risk.level === 'critical' || row.risk.level === 'high'
                ? 'rgba(254, 226, 226, 0.85)'
                : row.risk.level === 'medium'
                ? 'rgba(254, 243, 199, 0.85)'
                : 'rgba(209, 250, 229, 0.85)',
          }}
        >
          {row.risk.level} ({row.risk.score}/100)
        </span>
      ),
    },
    {
      key: 'submittedAt',
      header: 'Submission Date',
      render: (row) => (
        <span style={{ color: 'var(--dash-text-secondary)', fontSize: '0.88rem' }}>
          {new Date(row.submittedAt).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
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
          icon={<Eye size={14} />}
          onClick={() => navigate(`/applications/${row.id}`)}
        >
          Review
        </SecondaryButton>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="KYC Applications"
        subtitle="Manage and evaluate incoming identity verification requests and evidence."
        actions={
          <SecondaryButton
            icon={<Download size={15} />}
            onClick={() => alert('Exporting KYC application audit log (CSV)...')}
          >
            Export Log
          </SecondaryButton>
        }
      />

      <GlassPanel style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem' }}>
        <div className="dash-toolbar" style={{ margin: 0 }}>
          <div className="dash-toolbar-left">
            <SearchBar
              value={search}
              onChange={(val) => {
                setSearch(val);
                setPage(1);
              }}
              placeholder="Search by name, ID, doc number, email..."
              style={{ minWidth: 300 }}
            />

            <FilterBar onReset={handleResetFilters} showReset={hasActiveFilters}>
              <select
                className="dash-filter-select"
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value as ApplicationStatus | 'all');
                  setPage(1);
                }}
                aria-label="Filter by KYC status"
              >
                <option value="all">All Statuses</option>
                <option value="verified">Verified</option>
                <option value="pending">Pending</option>
                <option value="flagged">Flagged</option>
                <option value="review_required">Review Required</option>
              </select>

              <select
                className="dash-filter-select"
                value={docFilter}
                onChange={(e) => {
                  setDocFilter(e.target.value as DocumentType | 'all');
                  setPage(1);
                }}
                aria-label="Filter by document type"
              >
                <option value="all">All Documents</option>
                <option value="passport">Passport</option>
                <option value="national_id">National ID</option>
                <option value="drivers_license">Driver's License</option>
                <option value="residence_permit">Residence Permit</option>
              </select>

              <DateRangePicker
                startDate={dateRange.startDate}
                endDate={dateRange.endDate}
                onChange={(range) => {
                  setDateRange(range);
                  setPage(1);
                }}
              />
            </FilterBar>
          </div>
        </div>
      </GlassPanel>

      <GlassPanel>
        <DataTable
          columns={columns}
          rows={paginatedRows}
          rowKey={(r) => r.id}
          loading={loading}
          onRowClick={(r) => navigate(`/applications/${r.id}`)}
          emptyState={
            <EmptyState
              title="No applications match your criteria"
              description="Try clearing search filters or broadening your date window."
              action={
                hasActiveFilters ? (
                  <SecondaryButton onClick={handleResetFilters}>
                    Clear All Filters
                  </SecondaryButton>
                ) : undefined
              }
            />
          }
        />

        {!loading && filtered.length > 0 && (
          <TablePagination
            page={page}
            pageSize={PAGE_SIZE}
            total={filtered.length}
            onPageChange={setPage}
          />
        )}
      </GlassPanel>
    </>
  );
}

