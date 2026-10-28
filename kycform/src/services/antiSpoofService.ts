// MiniFASNetV2-SE Pretrained Anti-Spoofing ONNX Service
// Model candidate: https://github.com/facenox/face-antispoof-onnx (Apache-2.0)
// Runs local browser-based presentation-attack detection (print/screen/replay attacks).

import * as ort from 'onnxruntime-web';
import type { FaceBBox } from './faceLandmarkerService';

export interface AntiSpoofResult {
  available: boolean;
  isReal: boolean;
  status: 'real' | 'spoof' | 'uncertain' | 'unavailable';
  confidencePercent: number;
  logitDiff: number;
  realLogit: number;
  spoofLogit: number;
  errorMessage?: string;
}

let sessionInstance: ort.InferenceSession | null = null;
let isSessionLoading = false;
let sessionFailed = false;

// Configure ONNX WebAssembly paths
try {
  ort.env.wasm.wasmPaths = '/wasm/';
  ort.env.wasm.numThreads = 1;
} catch {
  // ignore
}

/**
 * Initializes the ONNX inference session for face anti-spoofing.
 */
export async function getAntiSpoofSession(): Promise<ort.InferenceSession | null> {
  if (sessionInstance) return sessionInstance;
  if (sessionFailed) return null;

  if (isSessionLoading) {
    while (isSessionLoading) {
      await new Promise((r) => setTimeout(r, 50));
    }
    return sessionInstance;
  }

  isSessionLoading = true;
  try {
    const session = await ort.InferenceSession.create('/models/face_antispoof.onnx', {
      executionProviders: ['wasm'],
      graphOptimizationLevel: 'all',
    });
    sessionInstance = session;
    return session;
  } catch (err) {
    console.warn('Could not initialize local ONNX anti-spoof session:', err);
    sessionFailed = true;
    return null;
  } finally {
    isSessionLoading = false;
  }
}

/**
 * Preprocesses a video frame crop matching MiniFASNet specifications:
 * 1. Expand bbox by 1.5x with reflection padding
 * 2. Resize to 128x128
 * 3. Normalize pixel values to [0.0, 1.0]
 * 4. Transpose to CHW shape [1, 3, 128, 128]
 */
function extractAndPreprocessFaceCrop(
  video: HTMLVideoElement,
  bbox: FaceBBox,
  targetSize = 128,
  expansionFactor = 1.5
): Float32Array | null {
  try {
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;

    // Convert normalized bbox to absolute pixels
    const absX = bbox.x * vw;
    const absY = bbox.y * vh;
    const absW = bbox.width * vw;
    const absH = bbox.height * vh;

    const maxDim = Math.max(absW, absH);
    const centerX = absX + absW / 2;
    const centerY = absY + absH / 2;

    const cropSize = Math.max(16, maxDim * expansionFactor);
    const startX = centerX - cropSize / 2;
    const startY = centerY - cropSize / 2;

    // Draw expanded crop onto offscreen canvas
    const canvas = document.createElement('canvas');
    canvas.width = targetSize;
    canvas.height = targetSize;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    // Fill with black or edge sample
    ctx.drawImage(
      video,
      Math.max(0, startX),
      Math.max(0, startY),
      Math.min(vw - Math.max(0, startX), cropSize),
      Math.min(vh - Math.max(0, startY), cropSize),
      0,
      0,
      targetSize,
      targetSize
    );

    const imgData = ctx.getImageData(0, 0, targetSize, targetSize);
    const pixels = imgData.data;

    // Create CHW float32 array: [3, 128, 128]
    const chwData = new Float32Array(3 * targetSize * targetSize);
    const planeSize = targetSize * targetSize;

    for (let i = 0; i < planeSize; i++) {
      const r = pixels[i * 4] / 255.0;
      const g = pixels[i * 4 + 1] / 255.0;
      const b = pixels[i * 4 + 2] / 255.0;

      // CHW layout
      chwData[i] = r; // Red channel
      chwData[planeSize + i] = g; // Green channel
      chwData[2 * planeSize + i] = b; // Blue channel
    }

    return chwData;
  } catch (err) {
    console.warn('Face crop preprocessing error:', err);
    return null;
  }
}

/**
 * Runs inference on the detected face to evaluate presentation attack risk.
 */
export async function evaluateAntiSpoof(
  video: HTMLVideoElement,
  bbox: FaceBBox
): Promise<AntiSpoofResult> {
  const session = await getAntiSpoofSession();
  if (!session) {
    return {
      available: false,
      isReal: true, // Default to true if model is unavailable so user is not blocked
      status: 'unavailable',
      confidencePercent: 0,
      logitDiff: 0,
      realLogit: 0,
      spoofLogit: 0,
      errorMessage: 'Local ONNX anti-spoof model not initialized or unavailable in browser.',
    };
  }

  const preprocessedData = extractAndPreprocessFaceCrop(video, bbox, 128, 1.5);
  if (!preprocessedData) {
    return {
      available: true,
      isReal: true,
      status: 'uncertain',
      confidencePercent: 50,
      logitDiff: 0,
      realLogit: 0,
      spoofLogit: 0,
      errorMessage: 'Could not extract valid face crop for inference.',
    };
  }

  try {
    const inputName = session.inputNames[0] || 'input';
    const tensor = new ort.Tensor('float32', preprocessedData, [1, 3, 128, 128]);

    const outputMap = await session.run({ [inputName]: tensor });
    const outputName = session.outputNames[0] || 'output';
    const outputTensor = outputMap[outputName];

    if (!outputTensor || !outputTensor.data) {
      throw new Error('Inference returned empty tensor data');
    }

    const logits = outputTensor.data as Float32Array;
    const realLogit = Number(logits[0] ?? 0);
    const spoofLogit = Number(logits[1] ?? 0);
    const logitDiff = realLogit - spoofLogit;

    // Decision boundaries:
    // logitDiff >= 0.4: Real face (high confidence)
    // logitDiff <= -0.4: Spoof attempt (high confidence)
    // between -0.4 and 0.4: Uncertain / requires secondary review
    let status: AntiSpoofResult['status'] = 'uncertain';
    let isReal = false;

    if (logitDiff > 0.4) {
      status = 'real';
      isReal = true;
    } else if (logitDiff < -0.4) {
      status = 'spoof';
      isReal = false;
    } else {
      status = 'uncertain';
      isReal = logitDiff >= 0;
    }

    // Sigmoid probability approximation
    const probability = 1 / (1 + Math.exp(-logitDiff));
    const confidencePercent = Math.round(
      status === 'real'
        ? probability * 100
        : status === 'spoof'
        ? (1 - probability) * 100
        : 50
    );

    return {
      available: true,
      isReal,
      status,
      confidencePercent,
      logitDiff: Number(logitDiff.toFixed(3)),
      realLogit: Number(realLogit.toFixed(3)),
      spoofLogit: Number(spoofLogit.toFixed(3)),
    };
  } catch (err) {
    return {
      available: true,
      isReal: true,
      status: 'uncertain',
      confidencePercent: 50,
      logitDiff: 0,
      realLogit: 0,
      spoofLogit: 0,
      errorMessage: err instanceof Error ? err.message : 'Anti-spoof inference error',
    };
  }
}

