import { Search, X } from 'lucide-react';

export interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  onClear?: () => void;
  className?: string;
  style?: React.CSSProperties;
}

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search...',
  onClear,
  className = '',
  style,
}: SearchBarProps) {
  return (
    <div className={`dash-search-bar ${className}`.trim()} style={style}>
      <Search size={16} />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
      {value && (
        <button
          type="button"
          onClick={() => {
            onChange('');
            onClear?.();
          }}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--dash-text-muted)', display: 'flex' }}
          aria-label="Clear search"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

