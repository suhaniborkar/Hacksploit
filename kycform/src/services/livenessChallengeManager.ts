// Active Liveness Challenge Manager
// Evaluates active challenge progress against calibrated neutral baselines.
// Provides immediate directional feedback, tolerance thresholds, and frame persistence.

import type { FaceAnalysisResult, FaceBaseline } from './faceLandmarkerService';

export type ChallengeType =
  | 'TURN_LEFT'
  | 'TURN_RIGHT'
  | 'LOOK_UP'
  | 'LOOK_DOWN'
  | 'BLINK'
  | 'HOLD_STILL';

export interface ChallengeDef {
  id: ChallengeType;
  title: string;
  instruction: string;
  directionCue: 'left' | 'right' | 'up' | 'down' | 'blink' | 'still';
  requiredFrames: number; // Consecutive frames condition must hold
  timeoutSeconds: number;
}

export interface ChallengeEvaluation {
  isSatisfied: boolean;
  feedback: string;
  directionState: 'correct' | 'wrong' | 'neutral';
  progressPercent: number;
}

export const ALL_CHALLENGES: Record<ChallengeType, ChallengeDef> = {
  TURN_LEFT: {
    id: 'TURN_LEFT',
    title: 'Turn Head Left',
    instruction: 'Slowly turn your head to your left',
    directionCue: 'left',
    requiredFrames: 3,
    timeoutSeconds: 14,
  },
  TURN_RIGHT: {
    id: 'TURN_RIGHT',
    title: 'Turn Head Right',
    instruction: 'Slowly turn your head to your right',
    directionCue: 'right',
    requiredFrames: 3,
    timeoutSeconds: 14,
  },
  LOOK_UP: {
    id: 'LOOK_UP',
    title: 'Look Up',
    instruction: 'Tilt your chin slightly upwards',
    directionCue: 'up',
    requiredFrames: 3,
    timeoutSeconds: 14,
  },
  LOOK_DOWN: {
    id: 'LOOK_DOWN',
    title: 'Look Down',
    instruction: 'Tilt your chin slightly downwards',
    directionCue: 'down',
    requiredFrames: 3,
    timeoutSeconds: 14,
  },
  BLINK: {
    id: 'BLINK',
    title: 'Blink Eyes',
    instruction: 'Blink both eyes naturally',
    directionCue: 'blink',
    requiredFrames: 2,
    timeoutSeconds: 14,
  },
  HOLD_STILL: {
    id: 'HOLD_STILL',
    title: 'Hold Still',
    instruction: 'Look straight at the camera and hold still',
    directionCue: 'still',
    requiredFrames: 8,
    timeoutSeconds: 14,
  },
};

/**
 * Evaluates whether the current frame meets the challenge condition relative to the calibrated baseline.
 * Provides granular, directional guidance to assist the applicant.
 */
export function evaluateChallengeFrame(
  challenge: ChallengeType,
  analysis: FaceAnalysisResult,
  baseline: FaceBaseline | null
): ChallengeEvaluation {
  if (analysis.status === 'no_face') {
    return {
      isSatisfied: false,
      feedback: 'Face out of frame — look directly at camera',
      directionState: 'neutral',
      progressPercent: 0,
    };
  }

  if (analysis.status === 'multiple_faces') {
    return {
      isSatisfied: false,
      feedback: 'Multiple faces detected — only 1 person must be visible',
      directionState: 'neutral',
      progressPercent: 0,
    };
  }

  // Use baseline if calibrated, or fallback to zero baseline
  const baseYaw = baseline ? baseline.yaw : 0;
  const basePitch = baseline ? baseline.pitch : 0;
  const baseCenterX = baseline ? baseline.centerX : 0.5;

  const deltaYaw = analysis.yaw - baseYaw;
  const deltaPitch = analysis.pitch - basePitch;

  switch (challenge) {
    case 'TURN_LEFT': {
      // User turns to their own anatomical left: deltaYaw > 0
      const THRESHOLD = 0.085;
      if (deltaYaw >= THRESHOLD) {
        return {
          isSatisfied: true,
          feedback: 'Good, hold that position…',
          directionState: 'correct',
          progressPercent: 100,
        };
      }
      if (deltaYaw >= 0.035) {
        return {
          isSatisfied: false,
          feedback: 'Turn a little further left',
          directionState: 'correct',
          progressPercent: Math.round((deltaYaw / THRESHOLD) * 100),
        };
      }
      if (deltaYaw <= -0.045) {
        return {
          isSatisfied: false,
          feedback: 'Moving in wrong direction — turn to your LEFT',
          directionState: 'wrong',
          progressPercent: 0,
        };
      }
      return {
        isSatisfied: false,
        feedback: 'Turn your head slowly to your left',
        directionState: 'neutral',
        progressPercent: 0,
      };
    }

    case 'TURN_RIGHT': {
      // User turns to their own anatomical right: deltaYaw < 0
      const THRESHOLD = -0.085;
      if (deltaYaw <= THRESHOLD) {
        return {
          isSatisfied: true,
          feedback: 'Good, hold that position…',
          directionState: 'correct',
          progressPercent: 100,
        };
      }
      if (deltaYaw <= -0.035) {
        return {
          isSatisfied: false,
          feedback: 'Turn a little further right',
          directionState: 'correct',
          progressPercent: Math.round((deltaYaw / THRESHOLD) * 100),
        };
      }
      if (deltaYaw >= 0.045) {
        return {
          isSatisfied: false,
          feedback: 'Moving in wrong direction — turn to your RIGHT',
          directionState: 'wrong',
          progressPercent: 0,
        };
      }
      return {
        isSatisfied: false,
        feedback: 'Turn your head slowly to your right',
        directionState: 'neutral',
        progressPercent: 0,
      };
    }

    case 'LOOK_UP': {
      // Tilt chin upwards: deltaPitch > 0
      const THRESHOLD = 0.075;
      if (deltaPitch >= THRESHOLD) {
        return {
          isSatisfied: true,
          feedback: 'Good, hold that position…',
          directionState: 'correct',
          progressPercent: 100,
        };
      }
      if (deltaPitch >= 0.03) {
        return {
          isSatisfied: false,
          feedback: 'Tilt chin a little higher',
          directionState: 'correct',
          progressPercent: Math.round((deltaPitch / THRESHOLD) * 100),
        };
      }
      if (deltaPitch <= -0.04) {
        return {
          isSatisfied: false,
          feedback: 'Moving down — tilt your chin UP',
          directionState: 'wrong',
          progressPercent: 0,
        };
      }
      return {
        isSatisfied: false,
        feedback: 'Tilt your chin slightly upwards',
        directionState: 'neutral',
        progressPercent: 0,
      };
    }

    case 'LOOK_DOWN': {
      // Tilt chin downwards: deltaPitch < 0
      const THRESHOLD = -0.065;
      if (deltaPitch <= THRESHOLD) {
        return {
          isSatisfied: true,
          feedback: 'Good, hold that position…',
          directionState: 'correct',
          progressPercent: 100,
        };
      }
      if (deltaPitch <= -0.025) {
        return {
          isSatisfied: false,
          feedback: 'Tilt chin a little lower',
          directionState: 'correct',
          progressPercent: Math.round((deltaPitch / THRESHOLD) * 100),
        };
      }
      if (deltaPitch >= 0.04) {
        return {
          isSatisfied: false,
          feedback: 'Moving up — tilt your chin DOWN',
          directionState: 'wrong',
          progressPercent: 0,
        };
      }
      return {
        isSatisfied: false,
        feedback: 'Tilt your chin slightly downwards',
        directionState: 'neutral',
        progressPercent: 0,
      };
    }

    case 'BLINK': {
      const blinkScore = Math.max(analysis.eyeBlinkLeft, analysis.eyeBlinkRight);
      if (analysis.isBlinking || (analysis.eyeBlinkLeft > 0.42 && analysis.eyeBlinkRight > 0.42)) {
        return {
          isSatisfied: true,
          feedback: 'Blink detected!',
          directionState: 'correct',
          progressPercent: 100,
        };
      }
      return {
        isSatisfied: false,
        feedback: 'Blink both eyes naturally',
        directionState: 'neutral',
        progressPercent: Math.round(blinkScore * 50),
      };
    }

    case 'HOLD_STILL': {
      const curCenterX = analysis.bbox ? analysis.bbox.centerX : baseCenterX;
      const dYaw = Math.abs(deltaYaw);
      const dPitch = Math.abs(deltaPitch);
      const dCenter = Math.abs(curCenterX - baseCenterX);

      // Realistic tolerance for normal breathing and landmark jitter
      const isWithinStillTolerance =
        dYaw < 0.055 &&
        dPitch < 0.055 &&
        dCenter < 0.045 &&
        analysis.eyeBlinkLeft < 0.45 &&
        analysis.eyeBlinkRight < 0.45;

      if (isWithinStillTolerance) {
        return {
          isSatisfied: true,
          feedback: 'Good, holding still… keep looking at camera',
          directionState: 'correct',
          progressPercent: 100,
        };
      }

      return {
        isSatisfied: false,
        feedback: 'Keep your face centered and look directly at camera',
        directionState: 'neutral',
        progressPercent: 0,
      };
    }

    default:
      return {
        isSatisfied: false,
        feedback: 'Follow on-screen instruction',
        directionState: 'neutral',
        progressPercent: 0,
      };
  }
}

/**
 * Generates a randomized sequence of 3 distinct, intuitive challenges for this session.
 */
export function generateRandomChallengeSequence(): ChallengeDef[] {
  // Pool 1: horizontal turn (Turn Left or Turn Right)
  // Pool 2: vertical tilt (Look Up or Look Down)
  // Pool 3: blink or hold still
  const pool1: ChallengeType[] = ['TURN_LEFT', 'TURN_RIGHT'];
  const pool2: ChallengeType[] = ['LOOK_UP', 'LOOK_DOWN'];
  const pool3: ChallengeType[] = ['BLINK', 'HOLD_STILL'];

  const ch1 = pool1[Math.floor(Math.random() * pool1.length)];
  const ch2 = pool2[Math.floor(Math.random() * pool2.length)];
  const ch3 = pool3[Math.floor(Math.random() * pool3.length)];

  const selected = [ch1, ch2, ch3];

  // Shuffle order
  for (let i = selected.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [selected[i], selected[j]] = [selected[j], selected[i]];
  }

  return selected.map((type) => ALL_CHALLENGES[type]);
}
