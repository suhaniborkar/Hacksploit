import { useState, useEffect } from 'react';
import { Download } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { ChartPanel, BarChart, LineChart, DonutChart, HBarChart } from '../components/ChartPanel';
import { SecondaryButton } from '../components/SecondaryButton';
import { LoadingState } from '../components/LoadingState';
import { dashboardService } from '../services/dashboardService';
import type { AnalyticsSeries } from '../types/dashboard';

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSeries | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const series = await dashboardService.getAnalytics();
        setData(series);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading || !data) {
    return <LoadingState message="Compiling analytics telemetry..." />;
  }

  return (
    <>
      <PageHeader
        title="Analytics & Compliance Reports"
        subtitle="Verification throughput, outcome ratios, and synthetic fraud detection trends."
        actions={
          <SecondaryButton
            icon={<Download size={15} />}
            onClick={() => alert('Generating PDF Executive Report...')}
          >
            Export Compliance Summary
          </SecondaryButton>
        }
      />

      <div className="dash-chart-grid">
        <ChartPanel
          title="Monthly Application Volume"
          subtitle="Total verification submissions over the past 6 months"
        >
          <BarChart data={data.volumeOverTime} />
        </ChartPanel>

        <ChartPanel
          title="Verification Outcome Distribution"
          subtitle="Proportion of verified, pending, review, and flagged outcomes"
        >
          <DonutChart data={data.outcomeDistribution} />
        </ChartPanel>

        <ChartPanel
          title="Applications by Document Type"
          subtitle="Volume breakdown by verified identity credential format"
        >
          <HBarChart data={data.byDocumentType} />
        </ChartPanel>

        <ChartPanel
          title="Fraud Flags & Rejections Over Time"
          subtitle="Monthly volume of identities confirmed or suspected synthetic"
        >
          <LineChart data={data.fraudFlagsOverTime} />
        </ChartPanel>
      </div>
    </>
  );
}

