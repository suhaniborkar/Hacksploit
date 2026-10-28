import type { ReactNode } from 'react';
import { LoadingState } from './LoadingState';
import { EmptyState } from './EmptyState';

export interface Column<T> {
  key: string;
  header: ReactNode;
  render?: (row: T, index: number) => ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string | number;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string | number;
  loading?: boolean;
  emptyState?: ReactNode;
  onRowClick?: (row: T) => void;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  emptyState,
  onRowClick,
  className = '',
}: DataTableProps<T>) {
  if (loading) {
    return <LoadingState message="Fetching data..." />;
  }

  if (rows.length === 0) {
    return emptyState ? (
      <>{emptyState}</>
    ) : (
      <EmptyState title="No records found" description="Try adjusting your search or filters." />
    );
  }

  return (
    <div className={`dash-table-wrapper ${className}`.trim()}>
      <table className="dash-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  textAlign: col.align || 'left',
                  width: col.width,
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={rowKey(row, idx)}
              onClick={() => onRowClick?.(row)}
              style={{ cursor: onRowClick ? 'pointer' : 'default' }}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  style={{
                    textAlign: col.align || 'left',
                  }}
                >
                  {col.render ? col.render(row, idx) : (row as Record<string, unknown>)[col.key] as ReactNode}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

