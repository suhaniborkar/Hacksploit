# Biometric Vision Integration — Backend Service Contract

## Overview

This document specifies the backend integration contract for **Biometric Vision** (`https://biometric.vision/products/liveness`, developer docs `https://guide.biometric.kz/en/`) to support genuine camera-based liveness verification in the VeriYID KYC frontend.

---

## Security Requirements

1. **Never expose the Biometric Vision Flow API key to the frontend client.**
   - All requests that use the provider's secret key (`api_key` or `flow_api_key`) must originate from the server.
   - Do **NOT** prefix secret keys with `VITE_` in frontend `.env`.

2. **Environment Variables on the Backend**:
   ```env
   BIOMETRIC_API_KEY="<YOUR_FLOW_API_KEY_FROM_BIOMETRIC_KZ>"
   BIOMETRIC_BASE_URL="https://kyc.biometric.kz"
   ```

---

## Backend Endpoints Specification

### 1. Create Liveness Session
Creates a unique session with Biometric Vision and returns the session ID to the frontend widget.

- **Frontend Route**: `POST /api/kyc/liveness/session`
- **Upstream Provider Call**: `POST https://kyc.biometric.kz/api/v1/flows/session/create/`

#### Request (Frontend &rarr; Backend):
```json
{
  "technology": "liveness",
  "locale": "en"
}
```

#### Backend Upstream Request (Backend &rarr; Biometric.kz):
```http
POST https://kyc.biometric.kz/api/v1/flows/session/create/
Content-Type: application/json

{
  "api_key": "<YOUR_FLOW_API_KEY>"
}
```

#### Upstream Response:
```json
{
  "session_id": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4"
}
```

#### Frontend Response (Backend &rarr; Frontend):
```json
{
  "sessionId": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4",
  "expiresInSeconds": 1800
}
```

---

### 2. Retrieve Verification Result
Called after the user finishes or aborts the verification flow in the browser. Queries Biometric Vision for genuine liveness metrics.

- **Frontend Route**: `POST /api/kyc/liveness/verify`
- **Upstream Provider Call**: `GET https://kyc.biometric.kz/api/v1/flows/session/result/?session_id=<session_id>&flow_api_key=<flow_api_key>`

#### Request (Frontend &rarr; Backend):
```json
{
  "sessionId": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4"
}
```

#### Backend Upstream Request (Backend &rarr; Biometric.kz):
```http
GET https://kyc.biometric.kz/api/v1/flows/session/result/?session_id=9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4&flow_api_key=<YOUR_FLOW_API_KEY>
```

#### Upstream Response Format:
```json
{
  "liveness_result": {
    "result": true,
    "prediction": "0.9980",
    "eye_closed": false,
    "face_center": true,
    "face_direction": "forward",
    "failure_reason": null
  },
  "face_photo": "data:image/jpeg;base64,..."
}
```

#### Frontend Response (Backend &rarr; Frontend):
```json
{
  "sessionId": "9a8b7c6d-5e4f-3a2b-1c0d-e9f8a7b6c5d4",
  "livenessPassed": true,
  "prediction": "0.9980",
  "scorePercent": 99.8,
  "eyeClosed": false,
  "faceCenter": true,
  "faceDirection": "forward",
  "facePhoto": "data:image/jpeg;base64,...",
  "failureReason": null
}
```

---

## Node.js / Express Example Implementation

```typescript
import express from 'express';
import fetch from 'node-fetch';

const app = express();
app.use(express.json());

const BIOMETRIC_API_KEY = process.env.BIOMETRIC_API_KEY;
const BIOMETRIC_BASE_URL = 'https://kyc.biometric.kz';

// 1. Session creation
app.post('/api/kyc/liveness/session', async (req, res) => {
  if (!BIOMETRIC_API_KEY) {
    return res.status(500).json({
      error: 'credentials_missing',
      message: 'BIOMETRIC_API_KEY is not configured on the backend server.'
    });
  }

  try {
    const response = await fetch(`${BIOMETRIC_BASE_URL}/api/v1/flows/session/create/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: BIOMETRIC_API_KEY }),
    });

    const data = await response.json();
    if (!response.ok) {
      return res.status(response.status).json(data);
    }

    res.json({
      sessionId: data.session_id,
      expiresInSeconds: 1800,
    });
  } catch (err: any) {
    res.status(502).json({ error: 'upstream_error', message: err.message });
  }
});

// 2. Result verification
app.post('/api/kyc/liveness/verify', async (req, res) => {
  const { sessionId } = req.body;
  if (!sessionId) {
    return res.status(400).json({ error: 'sessionId is required' });
  }

  try {
    const url = `${BIOMETRIC_BASE_URL}/api/v1/flows/session/result/?session_id=${encodeURIComponent(sessionId)}&flow_api_key=${encodeURIComponent(BIOMETRIC_API_KEY!)}`;
    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
      return res.status(response.status).json(data);
    }

    const liveness = data.liveness_result || {};
    res.json({
      sessionId,
      livenessPassed: Boolean(liveness.result === true),
      prediction: liveness.prediction || '0.98',
      scorePercent: Math.round(parseFloat(liveness.prediction || '0.98') * 100),
      eyeClosed: Boolean(liveness.eye_closed),
      faceCenter: Boolean(liveness.face_center ?? true),
      faceDirection: liveness.face_direction || 'forward',
      facePhoto: data.face_photo || null,
      failureReason: liveness.failure_reason || null,
    });
  } catch (err: any) {
    res.status(502).json({ error: 'upstream_error', message: err.message });
  }
});
```

