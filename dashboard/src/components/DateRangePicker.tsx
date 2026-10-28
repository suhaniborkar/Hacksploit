import { Calendar } from 'lucide-react';

export interface DateRangePickerProps {
  startDate: string;
  endDate: string;
  onChange: (range: { startDate: string; endDate: string }) => void;
  className?: string;
}

export function DateRangePicker({
  startDate,
  endDate,
  onChange,
  className = '',
}: DateRangePickerProps) {
  return (
    <div className={`dash-date-picker ${className}`.trim()}>
      <Calendar size={15} style={{ color: 'var(--dash-text-muted)' }} />
      <input
        type="date"
        value={startDate}
        onChange={(e) => onChange({ startDate: e.target.value, endDate })}
        aria-label="Start date"
        title="Start date"
      />
      <span>to</span>
      <input
        type="date"
        value={endDate}
        onChange={(e) => onChange({ startDate, endDate: e.target.value })}
        aria-label="End date"
        title="End date"
      />
    </div>
  );
}

