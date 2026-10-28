// MediaRecorder Service
// Captures a genuine short video recording of the applicant completing the active liveness challenges.
// Compiles the video Blob/File and extracts a high-resolution face portrait for document comparison.

export interface RecordedEvidence {
  videoBlob: Blob;
  videoFile: File;
  videoUrl: string;
  durationMs: number;
  faceSnapshotDataUrl: string | null;
}

export class VideoEvidenceRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private recordedChunks: Blob[] = [];
  private startTime = 0;
  private stream: MediaStream;

  constructor(stream: MediaStream) {
    this.stream = stream;
  }

  /**
   * Starts recording video chunks from the active camera stream.
   */
  start(): boolean {
    this.recordedChunks = [];
    this.startTime = Date.now();

    const mimeTypes = [
      'video/webm;codecs=vp8,opus',
      'video/webm;codecs=vp8',
      'video/webm',
      'video/mp4',
    ];

    let selectedMimeType = '';
    for (const mime of mimeTypes) {
      if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mime)) {
        selectedMimeType = mime;
        break;
      }
    }

    try {
      this.mediaRecorder = selectedMimeType
        ? new MediaRecorder(this.stream, { mimeType: selectedMimeType })
        : new MediaRecorder(this.stream);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };

      this.mediaRecorder.start(200); // 200ms timeslices
      return true;
    } catch (err) {
      console.warn('Could not initialize MediaRecorder:', err);
      this.mediaRecorder = null;
      return false;
    }
  }

  /**
   * Stops the recording and produces the final video Blob and File evidence.
   */
  async stop(videoElementForSnapshot?: HTMLVideoElement | null): Promise<RecordedEvidence> {
    const durationMs = Date.now() - this.startTime;

    // Capture face portrait snapshot from current video frame
    let faceSnapshotDataUrl: string | null = null;
    if (videoElementForSnapshot) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = videoElementForSnapshot.videoWidth || 640;
        canvas.height = videoElementForSnapshot.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          // Draw un-mirrored for standard KYC document comparison
          ctx.drawImage(
            videoElementForSnapshot,
            0,
            0,
            canvas.width,
            canvas.height
          );
          faceSnapshotDataUrl = canvas.toDataURL('image/jpeg', 0.92);
        }
      } catch (e) {
        console.warn('Snapshot capture error:', e);
      }
    }

    if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
      const emptyBlob = new Blob(this.recordedChunks, { type: 'video/webm' });
      return {
        videoBlob: emptyBlob,
        videoFile: new File([emptyBlob], `liveness-evidence-${Date.now()}.webm`, {
          type: 'video/webm',
        }),
        videoUrl: URL.createObjectURL(emptyBlob),
        durationMs,
        faceSnapshotDataUrl,
      };
    }

    return new Promise((resolve) => {
      if (!this.mediaRecorder) return;

      this.mediaRecorder.onstop = () => {
        const mimeType = this.mediaRecorder?.mimeType || 'video/webm';
        const videoBlob = new Blob(this.recordedChunks, { type: mimeType });
        const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
        const filename = `liveness-evidence-${Date.now()}.${ext}`;
        const videoFile = new File([videoBlob], filename, { type: mimeType });
        const videoUrl = URL.createObjectURL(videoBlob);

        resolve({
          videoBlob,
          videoFile,
          videoUrl,
          durationMs,
          faceSnapshotDataUrl,
        });
      };

      try {
        this.mediaRecorder.stop();
      } catch {
        // Fallback resolve if stop fails
        const fallbackBlob = new Blob(this.recordedChunks, { type: 'video/webm' });
        resolve({
          videoBlob: fallbackBlob,
          videoFile: new File([fallbackBlob], 'liveness-evidence.webm', { type: 'video/webm' }),
          videoUrl: URL.createObjectURL(fallbackBlob),
          durationMs,
          faceSnapshotDataUrl,
        });
      }
    });
  }
}

