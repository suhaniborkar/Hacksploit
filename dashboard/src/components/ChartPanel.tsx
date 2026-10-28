import type { ReactNode } from 'react';
import { GlassPanel } from './GlassPanel';
import type { ChartDataPoint, ChartDataPointColored } from '../types/dashboard';

/* ─── Bar Chart ──────────────────────────────────────────────────────── */
const BAR_COLOR = 'rgba(18, 63, 61, 0.65)';
const BAR_W = 40;
const BAR_GAP = 16;
const CHART_H = 170;
const CHART_PAD_L = 42;
const CHART_PAD_B = 36;

export interface BarChartProps {
  data: ChartDataPoint[];
}

export function BarChart({ data }: BarChartProps) {
  if (!data || data.length === 0) {
    return <p style={{ color: 'var(--dash-text-muted)', fontSize: '0.9rem' }}>No data points available.</p>;
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const width = CHART_PAD_L + data.length * (BAR_W + BAR_GAP) + BAR_GAP;
  const height = CHART_H + CHART_PAD_B + 10;

  return (
    <div className="dash-chart-svg-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label="Bar chart">
        {/* Y-axis */}
        <line
          x1={CHART_PAD_L}
          y1={10}
          x2={CHART_PAD_L}
          y2={CHART_H + 10}
          className="dash-chart-axis"
        />
        {/* X-axis */}
        <line
          x1={CHART_PAD_L}
          y1={CHART_H + 10}
          x2={width - 4}
          y2={CHART_H + 10}
          className="dash-chart-axis"
        />
        {/* Y-axis ticks */}
        {[0, 0.5, 1].map((frac) => {
          const y = 10 + CHART_H * (1 - frac);
          const label = Math.round(maxVal * frac);
          return (
            <g key={frac}>
              <line x1={CHART_PAD_L - 4} y1={y} x2={CHART_PAD_L} y2={y} stroke="rgba(0,0,0,0.2)" />
              <text x={CHART_PAD_L - 6} y={y + 4} textAnchor="end" className="dash-chart-text" fontSize={11}>
                {label}
              </text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const barH = Math.max(3, (d.value / maxVal) * CHART_H);
          const x = CHART_PAD_L + BAR_GAP + i * (BAR_W + BAR_GAP);
          const y = 10 + CHART_H - barH;
          return (
            <g key={d.label}>
              <rect
                x={x}
                y={y}
                width={BAR_W}
                height={barH}
                rx={4}
                fill={BAR_COLOR}
              >
                <title>{`${d.label}: ${d.value}`}</title>
              </rect>
              <text
                x={x + BAR_W / 2}
                y={CHART_H + 10 + 18}
                textAnchor="middle"
                className="dash-chart-text"
                fontSize={11}
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Horizontal Bar Chart ───────────────────────────────────────────── */
const H_BAR_H = 26;
const H_BAR_GAP = 12;
const H_CHART_W = 280;
const H_PAD_L = 130;

export interface HBarChartProps {
  data: ChartDataPoint[];
}

export function HBarChart({ data }: HBarChartProps) {
  if (!data || data.length === 0) {
    return <p style={{ color: 'var(--dash-text-muted)', fontSize: '0.9rem' }}>No data points available.</p>;
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const chartH = data.length * (H_BAR_H + H_BAR_GAP);
  const width = H_PAD_L + H_CHART_W + 50;

  return (
    <div className="dash-chart-svg-wrap">
      <svg viewBox={`0 0 ${width} ${chartH + 12}`} width={width} height={chartH + 12} role="img" aria-label="Horizontal bar chart">
        {data.map((d, i) => {
          const barW = Math.max(3, (d.value / maxVal) * H_CHART_W);
          const y = i * (H_BAR_H + H_BAR_GAP) + 6;
          return (
            <g key={d.label}>
              <text x={H_PAD_L - 10} y={y + H_BAR_H / 2 + 4} textAnchor="end" className="dash-chart-text" fontSize={12}>
                {d.label}
              </text>
              <rect x={H_PAD_L} y={y} width={barW} height={H_BAR_H} rx={4} fill={BAR_COLOR}>
                <title>{`${d.label}: ${d.value}`}</title>
              </rect>
              <text x={H_PAD_L + barW + 8} y={y + H_BAR_H / 2 + 4} className="dash-chart-text" fontSize={11} fontWeight={700}>
                {d.value}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Line Chart ─────────────────────────────────────────────────────── */
const L_CHART_W = 460;
const L_CHART_H = 160;
const L_PAD_L = 42;
const L_PAD_B = 32;

export interface LineChartProps {
  data: ChartDataPoint[];
}

export function LineChart({ data }: LineChartProps) {
  if (!data || data.length < 2) {
    return <p style={{ color: 'var(--dash-text-muted)', fontSize: '0.9rem' }}>Insufficient data for trend line.</p>;
  }

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const w = L_CHART_W;
  const h = L_CHART_H + L_PAD_B + 10;
  const step = (w - L_PAD_L - 20) / (data.length - 1);

  const points = data
    .map((d, i) => {
      const x = L_PAD_L + i * step;
      const y = 10 + L_CHART_H * (1 - d.value / maxVal);
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <div className="dash-chart-svg-wrap">
      <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} role="img" aria-label="Line chart">
        <line x1={L_PAD_L} y1={10} x2={L_PAD_L} y2={L_CHART_H + 10} className="dash-chart-axis" />
        <line x1={L_PAD_L} y1={L_CHART_H + 10} x2={w - 10} y2={L_CHART_H + 10} className="dash-chart-axis" />

        <polyline
          points={points}
          fill="none"
          stroke="rgba(18, 63, 61, 0.75)"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {data.map((d, i) => {
          const x = L_PAD_L + i * step;
          const y = 10 + L_CHART_H * (1 - d.value / maxVal);
          return (
            <g key={d.label}>
              <circle cx={x} cy={y} r={4.5} fill="var(--dash-accent)">
                <title>{`${d.label}: ${d.value}`}</title>
              </circle>
              <text x={x} y={L_CHART_H + 10 + 18} textAnchor="middle" className="dash-chart-text" fontSize={11}>
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ─── Donut Chart ────────────────────────────────────────────────────── */
const DONUT_R = 70;
const DONUT_INNER_R = 46;
const DONUT_CX = 95;
const DONUT_CY = 95;

export interface DonutChartProps {
  data: ChartDataPointColored[];
}

function polarToCart(cx: number, cy: number, r: number, angleDeg: number): [number, number] {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
}

function describeSector(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startAngle: number,
  endAngle: number
): string {
  const angleDelta = endAngle - startAngle;
  // Handle full circle
  const safeEnd = angleDelta >= 359.99 ? startAngle + 359.99 : endAngle;
  const [ox1, oy1] = polarToCart(cx, cy, outerR, startAngle);
  const [ox2, oy2] = polarToCart(cx, cy, outerR, safeEnd);
  const [ix1, iy1] = polarToCart(cx, cy, innerR, safeEnd);
  const [ix2, iy2] = polarToCart(cx, cy, innerR, startAngle);
  const large = angleDelta > 180 ? 1 : 0;
  return `M ${ox1} ${oy1} A ${outerR} ${outerR} 0 ${large} 1 ${ox2} ${oy2} L ${ix1} ${iy1} A ${innerR} ${innerR} 0 ${large} 0 ${ix2} ${iy2} Z`;
}

function computeSectors(data: ChartDataPointColored[], total: number) {
  let currentAngle = 0;
  return data.map((d) => {
    const angle = total > 0 ? (d.value / total) * 360 : 0;
    const start = currentAngle;
    const end = currentAngle + angle;
    currentAngle = end;
    return {
      ...d,
      path: describeSector(DONUT_CX, DONUT_CY, DONUT_R, DONUT_INNER_R, start, end),
      percentage: total > 0 ? Math.round((d.value / total) * 100) : 0,
    };
  });
}

export function DonutChart({ data }: DonutChartProps) {
  if (!data || data.length === 0) {
    return <p style={{ color: 'var(--dash-text-muted)', fontSize: '0.9rem' }}>No data points available.</p>;
  }

  const total = data.reduce((s, d) => s + d.value, 0);
  const sectors = computeSectors(data, total);

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
      <svg viewBox="0 0 190 190" width={190} height={190} role="img" aria-label="Donut distribution chart">
        {sectors.map((d) => (
          <path
            key={d.label}
            d={d.path}
            fill={d.color}
          >
            <title>{`${d.label}: ${d.value} (${d.percentage}%)`}</title>
          </path>
        ))}
        <text
          x={DONUT_CX}
          y={DONUT_CY - 4}
          textAnchor="middle"
          className="dash-chart-text"
          fontWeight="800"
          fontSize={20}
        >
          {total}
        </text>
        <text x={DONUT_CX} y={DONUT_CY + 14} textAnchor="middle" className="dash-chart-text" fontSize={11} fill="#666666">
          Total
        </text>
      </svg>

      <div className="dash-legend">
        {data.map((d) => (
          <div key={d.label} className="dash-legend-item">
            <span className="dash-legend-dot" style={{ background: d.color }} />
            <span>
              <strong>{d.label}:</strong> {d.value} ({total > 0 ? Math.round((d.value / total) * 100) : 0}%)
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Chart Panel Wrapper ────────────────────────────────────────────── */
export interface ChartPanelProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ChartPanel({ title, subtitle, actions, children, className = '' }: ChartPanelProps) {
  return (
    <GlassPanel className={`dash-chart-panel ${className}`.trim()}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div>
          <h2 className="dash-chart-title" style={{ margin: 0 }}>{title}</h2>
          {subtitle && <p style={{ fontSize: '0.85rem', color: 'var(--dash-text-muted)', marginTop: '0.2rem' }}>{subtitle}</p>}
        </div>
        {actions && <div>{actions}</div>}
      </div>
      {children}
    </GlassPanel>
  );
}
