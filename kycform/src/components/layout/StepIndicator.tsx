import { Check } from 'lucide-react';
import { useKYC } from '../../context/KYCContext';
import { STEPS, STEP_LABELS } from '../../types/kyc';
import type { KYCStep } from '../../types/kyc';

const FORM_STEPS: KYCStep[] = STEPS.filter(
  (s) => s !== 'welcome' && s !== 'results'
);

export function StepIndicator() {
  const { currentStep } = useKYC();

  if (currentStep === 'welcome' || currentStep === 'results') return null;

  const formIndex = FORM_STEPS.indexOf(currentStep);
  const total = FORM_STEPS.length;
  const pct = Math.round(((formIndex + 1) / total) * 100);

  return (
    <div className="step-indicator">
      <div className="step-progress-bar">
        <div className="step-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="step-list">
        {FORM_STEPS.map((step, i) => {
          const done = i < formIndex;
          const active = i === formIndex;
          return (
            <div
              key={step}
              className={`step-item ${active ? 'active' : ''} ${done ? 'done' : ''}`}
            >
              <div className="step-circle">
                {done ? <Check size={14} /> : <span>{i + 1}</span>}
              </div>
              <span className="step-label">{STEP_LABELS[step]}</span>
            </div>
          );
        })}
      </div>
      <p className="step-counter">
        Step {formIndex + 1} of {total} — {STEP_LABELS[currentStep]}
      </p>
    </div>
  );
}
