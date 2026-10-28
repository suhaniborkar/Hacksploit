import { useState, useEffect, useMemo } from 'react';
import { UserPlus, Trash2 } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { GlassPanel } from '../components/GlassPanel';
import { SearchBar } from '../components/SearchBar';
import { FilterBar } from '../components/FilterBar';
import { DataTable, type Column } from '../components/DataTable';
import { PrimaryButton } from '../components/PrimaryButton';
import { SecondaryButton } from '../components/SecondaryButton';
import { ConfirmationModal } from '../components/ConfirmationModal';
import { ToastNotification } from '../components/ToastNotification';
import { FormField } from '../components/FormField';
import { dashboardService } from '../services/dashboardService';
import type { DashboardUser, UserRole, ToastMessage } from '../types/dashboard';

export function UsersPage() {
  const [users, setUsers] = useState<DashboardUser[]>([]);
  const [loading, setLoading] = useState(true);

  // Search & Filter
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modal & Toast states
  const [showAddModal, setShowAddModal] = useState(false);
  const [userToDelete, setUserToDelete] = useState<DashboardUser | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  // Form states for new user
  const [newName, setNewName] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('reviewer');
  const [formError, setFormError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const u = await dashboardService.getUsers();
        setUsers(u);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      if (search) {
        const query = search.toLowerCase();
        const mName = u.name.toLowerCase().includes(query);
        const mEmail = u.email.toLowerCase().includes(query);
        if (!mName && !mEmail) return false;
      }
      if (roleFilter !== 'all' && u.role !== roleFilter) return false;
      if (statusFilter !== 'all' && u.status !== statusFilter) return false;
      return true;
    });
  }, [users, search, roleFilter, statusFilter]);

  const handleAddUser = async () => {
    if (!newName.trim() || !newEmail.trim()) {
      setFormError('Please enter both name and email.');
      return;
    }
    setFormError('');

    try {
      const created = await dashboardService.addUser({
        name: newName,
        email: newEmail,
        role: newRole,
        status: 'active',
      });
      setUsers((prev) => [created, ...prev]);
      setShowAddModal(false);
      setNewName('');
      setNewEmail('');
      setNewRole('reviewer');
      setToasts((prev) => [
        ...prev,
        {
          id: `toast-${Date.now()}`,
          type: 'success',
          title: 'User Added',
          message: `${created.name} successfully registered.`,
        },
      ]);
    } catch {
      setToasts((prev) => [
        ...prev,
        {
          id: `toast-${Date.now()}`,
          type: 'error',
          title: 'Error',
          message: 'Failed to create user.',
        },
      ]);
    }
  };

  const handleDeleteUser = async () => {
    if (!userToDelete) return;
    try {
      await dashboardService.deleteUser(userToDelete.id);
      setUsers((prev) => prev.filter((u) => u.id !== userToDelete.id));
      setToasts((prev) => [
        ...prev,
        {
          id: `toast-${Date.now()}`,
          type: 'info',
          title: 'User Removed',
          message: `${userToDelete.name} has been removed.`,
        },
      ]);
    } finally {
      setUserToDelete(null);
    }
  };

  const columns: Column<DashboardUser>[] = [
    {
      key: 'name',
      header: 'Team Member',
      render: (row) => (
        <div>
          <strong style={{ fontSize: '1rem' }}>{row.name}</strong>
          <div className="text-secondary" style={{ fontSize: '0.82rem' }}>
            {row.email}
          </div>
        </div>
      ),
    },
    {
      key: 'role',
      header: 'Access Role',
      render: (row) => (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '0.2rem 0.65rem',
            borderRadius: '999px',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--dash-text-primary)',
            background: 'rgba(255,255,255,0.7)',
            border: '1px solid rgba(0,0,0,0.08)',
            textTransform: 'capitalize',
          }}
        >
          {row.role}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Account Status',
      render: (row) => (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '0.2rem 0.65rem',
            borderRadius: '999px',
            fontSize: '0.82rem',
            fontWeight: 700,
            color: 'var(--dash-text-primary)',
            background:
              row.status === 'active'
                ? 'var(--badge-verified-bg)'
                : 'var(--badge-review-bg)',
            textTransform: 'capitalize',
          }}
        >
          {row.status}
        </span>
      ),
    },
    {
      key: 'lastLogin',
      header: 'Last Active Session',
      render: (row) => (
        <span style={{ fontSize: '0.88rem', color: 'var(--dash-text-secondary)' }}>
          {row.lastLogin !== 'Never'
            ? new Date(row.lastLogin).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })
            : 'Never'}
        </span>
      ),
    },
    {
      key: 'actions',
      header: 'Actions',
      align: 'right',
      render: (row) => (
        <SecondaryButton
          style={{ minHeight: 34, padding: '0.35rem 0.75rem', fontSize: '0.85rem' }}
          onClick={() => setUserToDelete(row)}
          disabled={row.role === 'admin' && users.filter((u) => u.role === 'admin').length <= 1}
          icon={<Trash2 size={14} />}
        >
          Remove
        </SecondaryButton>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        title="User & Access Management"
        subtitle="Manage compliance officers, fraud investigators, and auditor accounts."
        actions={
          <PrimaryButton
            icon={<UserPlus size={16} />}
            onClick={() => setShowAddModal(true)}
          >
            Invite Member
          </PrimaryButton>
        }
      />

      <GlassPanel style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem' }}>
        <div className="dash-toolbar" style={{ margin: 0 }}>
          <div className="dash-toolbar-left">
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search by name or email address..."
              style={{ minWidth: 280 }}
            />

            <FilterBar
              onReset={() => {
                setSearch('');
                setRoleFilter('all');
                setStatusFilter('all');
              }}
              showReset={search !== '' || roleFilter !== 'all' || statusFilter !== 'all'}
            >
              <select
                className="dash-filter-select"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                aria-label="Filter by role"
              >
                <option value="all">All Roles</option>
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="reviewer">Reviewer</option>
                <option value="viewer">Viewer</option>
              </select>

              <select
                className="dash-filter-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                aria-label="Filter by account status"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            </FilterBar>
          </div>
        </div>
      </GlassPanel>

      <GlassPanel>
        <DataTable
          columns={columns}
          rows={filteredUsers}
          rowKey={(r) => r.id}
          loading={loading}
        />
      </GlassPanel>

      {/* Add User Modal */}
      {showAddModal && (
        <ConfirmationModal
          title="Add Compliance Team Member"
          confirmLabel="Create Account"
          onConfirm={handleAddUser}
          onCancel={() => {
            setShowAddModal(false);
            setFormError('');
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <FormField label="Full Name" htmlFor="user-name" required error={formError && !newName ? 'Name is required' : undefined}>
              <input
                id="user-name"
                className="dash-form-input"
                placeholder="Elena Rostova"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </FormField>

            <FormField label="Email Address" htmlFor="user-email" required error={formError && !newEmail ? 'Email is required' : undefined}>
              <input
                id="user-email"
                type="email"
                className="dash-form-input"
                placeholder="elena.rostova@veriyid.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </FormField>

            <FormField label="Assign System Role" htmlFor="user-role">
              <select
                id="user-role"
                className="dash-filter-select"
                style={{ width: '100%' }}
                value={newRole}
                onChange={(e) => setNewRole(e.target.value as UserRole)}
              >
                <option value="admin">Admin (Full System Permissions)</option>
                <option value="analyst">Analyst (KYC & Fraud Screening)</option>
                <option value="reviewer">Reviewer (L1 Document Check)</option>
                <option value="viewer">Viewer (Read-Only Audit)</option>
              </select>
            </FormField>
          </div>
        </ConfirmationModal>
      )}

      {/* Delete Confirmation Modal */}
      {userToDelete && (
        <ConfirmationModal
          title={`Remove ${userToDelete.name}?`}
          description={`Are you sure you want to revoke system access for ${userToDelete.email}? This action takes effect immediately.`}
          confirmLabel="Remove User"
          isDanger
          onConfirm={handleDeleteUser}
          onCancel={() => setUserToDelete(null)}
        />
      )}

      {/* Toast Notifications */}
      <ToastNotification
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />
    </>
  );
}
