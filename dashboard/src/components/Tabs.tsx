export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ tabs, activeTab, onChange, className = '' }: TabsProps) {
  return (
    <div className={`dash-tabs ${className}`.trim()} role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`dash-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span
              style={{
                marginLeft: '0.45rem',
                fontSize: '0.78rem',
                padding: '0.1rem 0.45rem',
                borderRadius: '999px',
                background: activeTab === tab.id ? 'var(--dash-accent)' : 'rgba(0,0,0,0.06)',
                color: activeTab === tab.id ? '#ffffff' : 'var(--dash-text-primary)',
              }}
            >
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

