import { useState } from 'react';
import {
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Clock,
  Sparkles,
} from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { MetricCard } from '../components/MetricCard';
import { StatusBadge } from '../components/StatusBadge';
import { PrimaryButton } from '../components/PrimaryButton';
import { SecondaryButton } from '../components/SecondaryButton';
import { IconButton } from '../components/IconButton';
import { SearchBar } from '../components/SearchBar';
import { FilterBar } from '../components/FilterBar';
import { DateRangePicker } from '../components/DateRangePicker';
import { DataTable, type Column } from '../components/DataTable';
import { TablePagination } from '../components/TablePagination';
import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { ToastNotification } from '../components/ToastNotification';
import { FormField } from '../components/FormField';
import { Tabs } from '../components/Tabs';
import { ChartPanel, BarChart, DonutChart } from '../components/ChartPanel';
import type { ToastMessage } from '../types/dashboard';

interface SampleItem {
  id: string;
  name: string;
  role: string;
  status: string;
}

const SAMPLE_ROWS: SampleItem[] = [
  { id: '1', name: 'Arjun Mehta', role: 'Applicant', status: 'verified' },
  { id: '2', name: 'Priya Sharma', role: 'Applicant', status: 'pending' },
  { id: '3', name: 'Rajesh Varma', role: 'Applicant', status: 'flagged' },
];

export function ComponentShowcase() {
  const [modalOpen, setModalOpen] = useState(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [searchVal, setSearchVal] = useState('');
  const [dates, setDates] = useState({ startDate: '2026-10-01', endDate: '2026-10-28' });
  const [activeTab, setActiveTab] = useState('tab-1');
  const [page, setPage] = useState(1);

  const columns: Column<SampleItem>[] = [
    { key: 'name', header: 'Name', render: (r) => <strong>{r.name}</strong> },
    { key: 'role', header: 'Role' },
    { key: 'status', header: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  ];

  const triggerToast = (type: 'success' | 'error' | 'info') => {
    setToasts((prev) => [
      ...prev,
      {
        id: `toast-${Date.now()}`,
        type,
        title: `${type.toUpperCase()} Notification`,
        message: 'This is a sample design system alert notification.',
      },
    ]);
  };

  return (
    <>
      <PageHeader
        title="Design System & Component Showcase"
        subtitle="Verification of design tokens, translucent glass panels, and typography standards."
        actions={
          <PrimaryButton
            icon={<Sparkles size={16} />}
            onClick={() => triggerToast('success')}
          >
            Trigger Toast
          </PrimaryButton>
        }
      />

      {/* Typography & Design Rules Check */}
      <GlassPanel style={{ marginBottom: '1.5rem', padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginBottom: '0.5rem' }}>
          Strict Design Rule Validation
        </h2>
        <p style={{ color: 'var(--dash-text-secondary)', marginBottom: '1rem', fontSize: '0.95rem' }}>
          VeriYID mandates <strong>#111111</strong> near-black font color for all headings, text, metric labels, badges, links, and chart labels.
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <StatusBadge status="verified" />
          <StatusBadge status="pending" />
          <StatusBadge status="flagged" />
          <StatusBadge status="review_required" />
        </div>
      </GlassPanel>

      {/* Metric Cards */}
      <h2 style={{ fontSize: '1.15rem', fontWeight: 800, marginBottom: '0.75rem' }}>Metric Cards</h2>
      <div className="dash-metric-grid" style={{ marginBottom: '1.75rem' }}>
        <MetricCard label="Verified Ratio" value="98.2%" delta="+2.4%" deltaLabel="vs benchmark" icon={<CheckCircle size={22} />} />
        <MetricCard label="Synthetic Flags" value="42" delta="-12%" deltaLabel="under control" icon={<AlertTriangle size={22} />} />
        <MetricCard label="Avg. Latency" value="214ms" delta="Fast Path" icon={<Clock size={22} />} />
      </div>

      {/* Buttons & Input Controls */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '1.5rem', marginBottom: '1.75rem' }}>
        <GlassPanel style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '1rem' }}>Buttons & Actions</h3>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <PrimaryButton>Primary Button</PrimaryButton>
            <SecondaryButton>Secondary</SecondaryButton>
            <IconButton aria-label="Shield"><ShieldCheck size={18} /></IconButton>
            <button className="dash-btn-danger">Danger Action</button>
            <PrimaryButton loading>Loading</PrimaryButton>
          </div>
        </GlassPanel>

        <GlassPanel style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '1rem' }}>Search & Filter Inputs</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <SearchBar value={searchVal} onChange={setSearchVal} placeholder="Search anything..." />
            <FilterBar onReset={() => setDates({ startDate: '2026-10-01', endDate: '2026-10-28' })} showReset>
              <DateRangePicker startDate={dates.startDate} endDate={dates.endDate} onChange={setDates} />
            </FilterBar>
          </div>
        </GlassPanel>
      </div>

      {/* Form Fields & Tabs */}
      <GlassPanel style={{ marginBottom: '1.75rem', padding: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '1rem' }}>Form Fields & Navigation Tabs</h3>
        <Tabs
          tabs={[
            { id: 'tab-1', label: 'Tab Alpha', count: 3 },
            { id: 'tab-2', label: 'Tab Beta' },
            { id: 'tab-3', label: 'Tab Gamma', count: 12 },
          ]}
          activeTab={activeTab}
          onChange={setActiveTab}
        />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
          <FormField label="Standard Input" htmlFor="demo-1" hint="This is a helper hint for the user.">
            <input id="demo-1" className="dash-form-input" placeholder="Type here..." />
          </FormField>
          <FormField label="Required Field with Validation" htmlFor="demo-2" required error="Field verification failed.">
            <input id="demo-2" className="dash-form-input" defaultValue="Invalid input sample" />
          </FormField>
        </div>
      </GlassPanel>

      {/* Data Table & Pagination */}
      <GlassPanel style={{ marginBottom: '1.75rem' }}>
        <div className="dash-section-heading">DataTable with Reusable Rows</div>
        <DataTable columns={columns} rows={SAMPLE_ROWS} rowKey={(r) => r.id} />
        <TablePagination page={page} pageSize={2} total={SAMPLE_ROWS.length} onPageChange={setPage} />
      </GlassPanel>

      {/* State Indicators */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
        <GlassPanel><LoadingState message="Demonstrating Loading State..." /></GlassPanel>
        <GlassPanel><EmptyState title="Demonstrating Empty State" description="When no records match the criteria." /></GlassPanel>
        <GlassPanel><ErrorState title="Demonstrating Error State" message="When the network fails." onRetry={() => {}} /></GlassPanel>
      </div>

      {/* Chart Panels */}
      <div className="dash-chart-grid" style={{ marginBottom: '1.75rem' }}>
        <ChartPanel title="Sample Bar Chart">
          <BarChart data={[{ label: 'A', value: 10 }, { label: 'B', value: 25 }, { label: 'C', value: 18 }]} />
        </ChartPanel>
        <ChartPanel title="Sample Donut Chart">
          <DonutChart data={[{ label: 'Low', value: 60, color: 'rgba(52,168,83,0.65)' }, { label: 'High', value: 20, color: 'rgba(234,67,53,0.65)' }]} />
        </ChartPanel>
      </div>

      {/* Modal Trigger Demonstration */}
      <div style={{ textAlign: 'center', margin: '2rem 0' }}>
        <PrimaryButton onClick={() => setModalOpen(true)}>
          Open Confirmation Modal Demo
        </PrimaryButton>
      </div>

      {modalOpen && (
        <ConfirmationModal
          title="Design System Modal Demonstration"
          description="Glassmorphic modal dialog with backdrop blur, customizable actions, and keyboard accessible structure."
          onConfirm={() => {
            setModalOpen(false);
            triggerToast('info');
          }}
          onCancel={() => setModalOpen(false)}
        />
      )}

      <ToastNotification toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))} />
    </>
  );
}
