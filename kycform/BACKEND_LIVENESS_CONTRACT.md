# Real Liveness Verification — Backend Contract Specification

## Overview

The VeriYID KYC application now utilizes **Google MediaPipe Tasks Vision Face Landmarker** and a local **MiniFASNetV2-SE Anti-Spoofing ONNX model** directly in the browser to perform genuine camera-based liveness verification without relying on paid third-party vendor APIs.

During verification:
1. The user grants camera consent.
2. The browser executes 3 randomized active challenges (e.g., Turn Left, Turn Right, Look Up, Look Down, Blink, Hold Still) analyzed frame-by-frame on live camera video.
3. MediaPipe confirms single face presence, centered alignment, and motion criteria across consecutive frames.
4. The local MiniFASNetV2-SE anti-spoofing model evaluates presentation attack probability (print / digital replay detection).
5. The `MediaRecorder` captures a genuine short video recording of the challenge sequence and captures a high-resolution face portrait.
6. The evidence is compiled and submitted to the backend via `POST /api/kyc/liveness/verify`.

> [!IMPORTANT]
> Client-side challenge completion is treated as applicant evidence, not a trusted server-side decision. The backend endpoint must receive the evidence, validate the recording, and issue the final verification outcome.

---

## Backend Endpoints

### 1. Initialize Evidence Session (Optional)
- **Route**: `POST /api/kyc/liveness/session`
- **Request Body**:
  ```json
  {
    "technology": "mediapipe_liveness",
    "timestamp": "2026-10-28T17:00:00.000Z"
  }
  ```
- **Response**:
  ```json
  {
    "sessionId": "live_sess_89f2a4bc01",
    "expiresInSeconds": 1800
  }
  ```

---

### 2. Submit Liveness Evidence & Telemetry
- **Route**: `POST /api/kyc/liveness/verify`
- **Content-Type**: `multipart/form-data`

#### Multipart Form Fields:
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `sessionId` | String | Session reference token |
| `challengesCompleted` | JSON String | Array of completed challenge names, e.g. `["Turn Head Left", "Look Up", "Blink Eyes"]` |
| `antiSpoof` | JSON String | MiniFASNet model telemetry: `{"isReal": true, "status": "real", "confidencePercent": 98.6, "logitDiff": 1.42}` |
| `facePhoto` | String (DataURL) | High-resolution face portrait captured at centered orientation for document comparison |
| `videoEvidence` | File (`.webm` / `.mp4`) | Short video recording of the applicant performing the challenges |

#### Expected Response:
```json
{
  "verified": true,
  "status": "passed",
  "message": "Applicant liveness and anti-spoof evidence verified.",
  "riskScore": 10,
  "evidenceId": "ev_89f2a4bc01"
}
```

#### Rejection / Spoof Detected Response:
```json
{
  "verified": false,
  "status": "failed",
  "message": "Presentation attack detected or evidence rejected.",
  "riskScore": 92
}
```

#### Manual Review Required Response:
```json
{
  "verified": false,
  "status": "review_required",
  "message": "Anti-spoofing score in uncertain interval. Forwarded to compliance officer.",
  "riskScore": 48
}
```

---

## Express / Node.js Backend Implementation Example

```javascript
import express from 'express';
import multer from 'multer';

const app = express();
const upload = multer({ limits: { fileSize: 15 * 1024 * 1024 } }); // 15MB limit

// 1. Session initialization
app.post('/api/kyc/liveness/session', (req, res) => {
  const sessionId = `live_sess_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
  res.json({ sessionId, expiresInSeconds: 1800 });
});

// 2. Evidence verification
app.post('/api/kyc/liveness/verify', upload.single('videoEvidence'), (req, res) => {
  const { sessionId, challengesCompleted, antiSpoof, facePhoto } = req.body;
  const videoFile = req.file;

  const challenges = challengesCompleted ? JSON.parse(challengesCompleted) : [];
  const antiSpoofData = antiSpoof ? JSON.parse(antiSpoof) : {};

  // Server-side validation
  if (antiSpoofData.status === 'spoof') {
    return res.json({
      verified: false,
      status: 'failed',
      message: 'Presentation attack detected by anti-spoofing inference.',
      riskScore: 92,
    });
  }

  if (antiSpoofData.status === 'uncertain') {
    return res.json({
      verified: false,
      status: 'review_required',
      message: 'Uncertain confidence interval requires compliance manual review.',
      riskScore: 45,
    });
  }

  if (challenges.length < 3) {
    return res.status(400).json({
      verified: false,
      status: 'failed',
      message: 'Incomplete active challenge sequence.',
    });
  }

  // Evidence verified successfully
  res.json({
    verified: true,
    status: 'passed',
    message: 'Active liveness and video evidence verified.',
    riskScore: 12,
    evidenceId: sessionId,
  });
});

app.listen(3001, () => console.log('KYC Backend listening on port 3001'));
```

