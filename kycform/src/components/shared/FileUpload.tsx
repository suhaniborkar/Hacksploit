import { useCallback, useRef, useState } from 'react';
import { Upload, X, RefreshCw, Image } from 'lucide-react';

interface FileUploadProps {
  label: string;
  side?: 'front' | 'back';
  preview?: string;
  onFileSelected: (file: File, dataUrl: string) => void;
  onRemove?: () => void;
  accept?: string;
  maxSizeMB?: number;
  required?: boolean;
  error?: string;
}

const MAX_SIZE_MB = 5;
const ACCEPTED = 'image/jpeg,image/png,image/webp,application/pdf';

export function FileUpload({
  label,
  side,
  preview,
  onFileSelected,
  onRemove,
  accept = ACCEPTED,
  maxSizeMB = MAX_SIZE_MB,
  required,
  error,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const processFile = useCallback(
    async (file: File) => {
      setLocalError(null);
      const allowedTypes = accept.split(',');
      if (!allowedTypes.includes(file.type)) {
        setLocalError(`Unsupported file type. Allowed: JPEG, PNG, WebP, PDF.`);
        return;
      }
      if (file.size > maxSizeMB * 1024 * 1024) {
        setLocalError(`File is too large. Maximum size is ${maxSizeMB} MB.`);
        return;
      }
      setUploading(true);
      const reader = new FileReader();
      reader.onload = (e) => {
        const dataUrl = e.target?.result as string;
        onFileSelected(file, dataUrl);
        setUploading(false);
      };
      reader.onerror = () => {
        setLocalError('Failed to read the file. Please try again.');
        setUploading(false);
      };
      reader.readAsDataURL(file);
    },
    [accept, maxSizeMB, onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
    },
    [processFile]
  );

  const displayError = error || localError;

  const sideLabel = side ? ` (${side === 'front' ? 'Front side' : 'Back side'})` : '';

  return (
    <div className={`file-upload ${dragOver ? 'drag-over' : ''} ${displayError ? 'upload-error' : ''}`}>
      <p className="upload-label">
        {label}{sideLabel}
        {required && <span className="required-mark" aria-hidden="true"> *</span>}
      </p>

      {preview ? (
        <div className="upload-preview">
          {preview.startsWith('data:image') ? (
            <img src={preview} alt={`${label} preview`} className="preview-img" />
          ) : (
            <div className="preview-pdf">
              <Image size={32} /> PDF uploaded
            </div>
          )}
          <div className="preview-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => inputRef.current?.click()}
            >
              <RefreshCw size={14} /> Replace
            </button>
            {onRemove && (
              <button type="button" className="btn btn-danger btn-sm" onClick={onRemove}>
                <X size={14} /> Remove
              </button>
            )}
          </div>
        </div>
      ) : (
        <div
          className="upload-drop-zone"
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label={`Upload ${label}${sideLabel}`}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
        >
          {uploading ? (
            <div className="upload-progress">
              <div className="spinner spinner-sm" />
              <p>Reading file…</p>
            </div>
          ) : (
            <>
              <Upload size={32} className="upload-icon" />
              <p className="upload-cta">Click to upload or drag & drop</p>
              <p className="upload-hint">JPEG, PNG, WebP or PDF · Max {maxSizeMB} MB</p>
            </>
          )}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="sr-only"
        onChange={handleChange}
        aria-hidden="true"
      />

      {displayError && (
        <p className="field-error" role="alert">{displayError}</p>
      )}
    </div>
  );
}
