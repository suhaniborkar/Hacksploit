// MediaPipe Tasks Vision Face Landmarker Service
// Performs real, local, in-browser facial landmark tracking, head pose estimation, and blink detection.

import { FilesetResolver, FaceLandmarker } from '@mediapipe/tasks-vision';

export interface FaceBBox {
  x: number;
  y: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
}

export interface FaceBaseline {
  yaw: number;
  pitch: number;
  centerX: number;
  centerY: number;
  faceWidth: number;
}

export interface FaceAnalysisResult {
  faceCount: number;
  status: 'no_face' | 'multiple_faces' | 'off_center' | 'too_far' | 'too_close' | 'ready';
  message: string;
  bbox?: FaceBBox;
  yaw: number; // Normalized horizontal turn ratio
  pitch: number; // Normalized vertical tilt ratio
  roll: number;
  isCentered: boolean;
  isDistanceOk: boolean;
  eyeBlinkLeft: number; // 0.0 (open) to 1.0 (closed)
  eyeBlinkRight: number;
  isBlinking: boolean;
  landmarks?: Array<{ x: number; y: number; z: number }>;
}

let landmarkerInstance: FaceLandmarker | null = null;
let isInitializing = false;

/**
 * Initializes the MediaPipe Face Landmarker.
 * Loads local wasm and model first, falling back to CDN if necessary.
 */
export async function getFaceLandmarker(): Promise<FaceLandmarker> {
  if (landmarkerInstance) {
    return landmarkerInstance;
  }

  if (isInitializing) {
    while (isInitializing) {
      await new Promise((r) => setTimeout(r, 50));
    }
    if (landmarkerInstance) return landmarkerInstance;
  }

  isInitializing = true;
  try {
    let filesetResolver;
    try {
      filesetResolver = await FilesetResolver.forVisionTasks('/wasm/mediapipe');
    } catch {
      filesetResolver = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.2.0/wasm'
      );
    }

    let landmarker: FaceLandmarker;
    try {
      landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: {
          modelAssetPath: '/models/face_landmarker.task',
          delegate: 'GPU',
        },
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
        runningMode: 'VIDEO',
        numFaces: 2, // Detects multiple faces to prevent spoofing
      });
    } catch {
      // Fallback to CPU delegate and CDN asset
      landmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: {
          modelAssetPath:
            'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
          delegate: 'CPU',
        },
        outputFaceBlendshapes: true,
        outputFacialTransformationMatrixes: true,
        runningMode: 'VIDEO',
        numFaces: 2,
      });
    }

    landmarkerInstance = landmarker;
    return landmarker;
  } finally {
    isInitializing = false;
  }
}

/**
 * Releases the FaceLandmarker resources when unmounting or exiting.
 */
export function releaseFaceLandmarker(): void {
  if (landmarkerInstance) {
    try {
      landmarkerInstance.close();
    } catch {
      // ignore
    }
    landmarkerInstance = null;
  }
}

/**
 * Analyzes a single camera video frame.
 */
export function analyzeFaceFrame(
  landmarker: FaceLandmarker,
  videoElement: HTMLVideoElement,
  timestampMs: number
): FaceAnalysisResult {
  if (!videoElement || videoElement.readyState < 2) {
    return {
      faceCount: 0,
      status: 'no_face',
      message: 'Initializing camera feed…',
      yaw: 0,
      pitch: 0,
      roll: 0,
      isCentered: false,
      isDistanceOk: false,
      eyeBlinkLeft: 0,
      eyeBlinkRight: 0,
      isBlinking: false,
    };
  }

  const results = landmarker.detectForVideo(videoElement, timestampMs);
  const faceCount = results.faceLandmarks ? results.faceLandmarks.length : 0;

  if (faceCount === 0) {
    return {
      faceCount: 0,
      status: 'no_face',
      message: 'No face detected. Please position yourself in front of the camera.',
      yaw: 0,
      pitch: 0,
      roll: 0,
      isCentered: false,
      isDistanceOk: false,
      eyeBlinkLeft: 0,
      eyeBlinkRight: 0,
      isBlinking: false,
    };
  }

  if (faceCount > 1) {
    return {
      faceCount,
      status: 'multiple_faces',
      message: 'Multiple faces detected. Only one person must be visible.',
      yaw: 0,
      pitch: 0,
      roll: 0,
      isCentered: false,
      isDistanceOk: false,
      eyeBlinkLeft: 0,
      eyeBlinkRight: 0,
      isBlinking: false,
    };
  }

  const landmarks = results.faceLandmarks[0];

  // 1. Compute Face Bounding Box
  let minX = 1;
  let maxX = 0;
  let minY = 1;
  let maxY = 0;

  for (let i = 0; i < landmarks.length; i++) {
    const lm = landmarks[i];
    if (lm.x < minX) minX = lm.x;
    if (lm.x > maxX) maxX = lm.x;
    if (lm.y < minY) minY = lm.y;
    if (lm.y > maxY) maxY = lm.y;
  }

  const bbox: FaceBBox = {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
    centerX: (minX + maxX) / 2,
    centerY: (minY + maxY) / 2,
  };

  // 2. Validate position & distance within the oval guide
  // Centered criteria: within [0.32, 0.68] horizontally and [0.26, 0.72] vertically
  const isCentered =
    bbox.centerX >= 0.32 &&
    bbox.centerX <= 0.68 &&
    bbox.centerY >= 0.26 &&
    bbox.centerY <= 0.72;

  const isTooFar = bbox.width < 0.20;
  const isTooClose = bbox.width > 0.68;
  const isDistanceOk = !isTooFar && !isTooClose;

  // 3. Stable 3D Head Pose Landmark Ratios
  // Landmark 1: Nose tip
  // Landmark 234: Right cheek edge (person's anatomical right; smaller X in camera coordinate)
  // Landmark 454: Left cheek edge (person's anatomical left; larger X in camera coordinate)
  // Landmark 10: Forehead top
  // Landmark 152: Chin bottom
  const nose = landmarks[1];
  const rightCheek = landmarks[234];
  const leftCheek = landmarks[454];
  const forehead = landmarks[10];
  const chin = landmarks[152];

  // Horizontal span between cheeks
  const cheekSpan = Math.abs(leftCheek.x - rightCheek.x) || 0.1;
  const distFromRightCheek = Math.abs(nose.x - rightCheek.x);
  const distFromLeftCheek = Math.abs(leftCheek.x - nose.x);

  // Yaw Ratio:
  // When person turns to their LEFT (toward leftCheek 454): nose.x increases, distFromRightCheek grows, distFromLeftCheek shrinks.
  // Result is positive.
  // When person turns to their RIGHT (toward rightCheek 234): distFromRightCheek shrinks, distFromLeftCheek grows.
  // Result is negative.
  const yaw = (distFromRightCheek - distFromLeftCheek) / cheekSpan;

  // Vertical span between forehead and chin
  const faceHeight = Math.abs(chin.y - forehead.y) || 0.1;
  const distForeheadToNose = Math.abs(nose.y - forehead.y);
  const distNoseToChin = Math.abs(chin.y - nose.y);

  // Pitch Ratio:
  // When person tilts head UP: chin rises, nose.y moves closer to forehead.y. distNoseToChin grows, distForeheadToNose shrinks.
  // Result is positive.
  // When person tilts head DOWN: chin drops, nose moves toward chin. distNoseToChin shrinks, distForeheadToNose grows.
  // Result is negative.
  const pitch = (distNoseToChin - distForeheadToNose) / faceHeight;

  // Roll: angle between left and right cheek
  const roll = Math.atan2(leftCheek.y - rightCheek.y, leftCheek.x - rightCheek.x);

  // 4. Blink Detection via Blendshapes with EAR Fallback
  let eyeBlinkLeft = 0;
  let eyeBlinkRight = 0;

  if (results.faceBlendshapes && results.faceBlendshapes[0]) {
    const categories = results.faceBlendshapes[0].categories;
    for (let c = 0; c < categories.length; c++) {
      const cat = categories[c];
      if (cat.categoryName === 'eyeBlinkLeft') {
        eyeBlinkLeft = cat.score;
      } else if (cat.categoryName === 'eyeBlinkRight') {
        eyeBlinkRight = cat.score;
      }
    }
  } else {
    // Landmark EAR calculation
    const rEyeH = Math.abs(landmarks[159].y - landmarks[145].y);
    const rEyeW = Math.abs(landmarks[33].x - landmarks[133].x) || 1;
    const lEyeH = Math.abs(landmarks[386].y - landmarks[374].y);
    const lEyeW = Math.abs(landmarks[362].x - landmarks[263].x) || 1;

    eyeBlinkLeft = lEyeH / lEyeW < 0.16 ? 0.85 : 0.05;
    eyeBlinkRight = rEyeH / rEyeW < 0.16 ? 0.85 : 0.05;
  }

  const isBlinking = eyeBlinkLeft > 0.45 && eyeBlinkRight > 0.45;

  let status: FaceAnalysisResult['status'] = 'ready';
  let message = 'Face centered';

  if (!isCentered) {
    status = 'off_center';
    message = 'Center your face inside the oval guide';
  } else if (isTooFar) {
    status = 'too_far';
    message = 'Move slightly closer to the camera';
  } else if (isTooClose) {
    status = 'too_close';
    message = 'Move slightly farther back from the camera';
  }

  return {
    faceCount: 1,
    status,
    message,
    bbox,
    yaw,
    pitch,
    roll,
    isCentered,
    isDistanceOk,
    eyeBlinkLeft,
    eyeBlinkRight,
    isBlinking,
    landmarks: landmarks.map((l) => ({ x: l.x, y: l.y, z: l.z })),
  };
}
