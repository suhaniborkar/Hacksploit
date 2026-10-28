import { Calendar, Tag } from 'lucide-react';
import { format } from 'date-fns';

interface ApplicationSummaryProps {
  applicationRef: string;
  submittedAt: string;
}

export function ApplicationSummary({ applicationRef, submittedAt }: ApplicationSummaryProps) {
  const formattedDate = (() => {
    try {
      return format(new Date(submittedAt), 'dd MMM yyyy, HH:mm:ss');
    } catch {
      return submittedAt;
    }
  })();

  return (
    <div className="application-summary">
      <div className="summary-item">
        <Tag size={16} className="summary-icon" />
        <div>
          <span className="summary-label">Application Reference</span>
          <span className="summary-value summary-ref">{applicationRef}</span>
        </div>
      </div>
      <div className="summary-item">
        <Calendar size={16} className="summary-icon" />
        <div>
          <span className="summary-label">Submitted At</span>
          <span className="summary-value">{formattedDate}</span>
        </div>
      </div>
    </div>
  );
}

