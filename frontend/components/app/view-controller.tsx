'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { ConnectionQuality } from 'livekit-client';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import {
  useAgent,
  useLocalParticipant,
  useSessionContext,
} from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { Button } from '@/components/ui/button';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

/**
 * Connecting overlay shown during agent connection with network-slow awareness.
 */
function ConnectingView({ isNetworkSlow }: { isNetworkSlow: boolean }) {
  return (
    <motion.div
      key="connecting"
      {...VIEW_MOTION_PROPS}
      className="bg-background flex h-svh flex-col items-center justify-center px-6 text-center"
    >
      {/* Spinner */}
      <div className="mb-6">
        <div className="border-primary/20 border-t-primary mx-auto size-12 animate-spin rounded-full border-4" />
      </div>

      <p className="text-foreground text-base font-semibold">
        DhanSathi से जुड़ रहे हैं…
      </p>
      <p className="text-muted-foreground mt-1 text-sm">
        Connecting to DhanSathi…
      </p>

      {/* Network slow warning */}
      {isNetworkSlow && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-caution/10 border-caution/20 mt-6 max-w-sm rounded-xl border px-4 py-3"
        >
          <p className="text-caution text-xs font-medium md:text-sm">
            ⚠️ आपका इंटरनेट धीमा है, कृपया प्रतीक्षा करें
          </p>
          <p className="text-caution/70 mt-0.5 text-[10px] md:text-xs">
            Your connection seems slow, please wait
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}

/**
 * Call ended view shown after disconnect with follow-up actions.
 */
function CallEndedView({ onStartAgain }: { onStartAgain: () => void }) {
  return (
    <motion.div
      key="call-ended"
      {...VIEW_MOTION_PROPS}
      className="bg-background flex h-svh flex-col items-center justify-center px-6 text-center"
    >
      {/* Checkmark icon */}
      <div className="bg-success/10 mb-6 flex size-16 items-center justify-center rounded-full">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-success"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>

      <h2 className="text-foreground text-lg font-bold md:text-xl">
        बातचीत समाप्त हुई
      </h2>
      <p className="text-muted-foreground mt-1 text-sm">
        Conversation ended
      </p>

      <p className="text-muted-foreground mt-4 max-w-sm text-xs leading-5 md:text-sm">
        DhanSathi से बात करने के लिए धन्यवाद। क्या आप कुछ और जानना चाहते हैं?
        <br />
        <span className="text-muted-foreground/70">
          Thanks for talking to DhanSathi. Would you like to know more?
        </span>
      </p>

      {/* Follow-up actions */}
      <div className="mt-6 flex flex-col gap-3">
        <Button
          size="lg"
          onClick={onStartAgain}
          className="animate-glow-amber w-72 rounded-full font-sans text-sm font-bold"
        >
          फिर से बात करें · Talk Again
        </Button>
      </div>
    </motion.div>
  );
}

/**
 * Determine the top-level UI state from LiveKit's agent/session state.
 *
 * State mapping:
 *   disconnected + !hasBeenConnected  →  'ready'
 *   connecting/pre-connect-buffering/initializing/idle  →  'connecting'
 *   listening/thinking/speaking  →  'in-call'
 *   disconnected/failed + hasBeenConnected  →  'call-ended'
 */
type UIState = 'ready' | 'connecting' | 'in-call' | 'call-ended';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const agent = useAgent();
  const { resolvedTheme } = useTheme();
  const { localParticipant } = useLocalParticipant();

  // Track if we've ever been connected to distinguish "not started yet" from "call ended"
  const hasBeenConnectedRef = useRef(false);
  const [hasEnded, setHasEnded] = useState(false);
  const [isStarting, setIsStarting] = useState(false);

  useEffect(() => {
    if (isConnected) {
      hasBeenConnectedRef.current = true;
      setIsStarting(false);
      setHasEnded(false);
    }
  }, [isConnected]);

  useEffect(() => {
    if (!isConnected && hasBeenConnectedRef.current) {
      setHasEnded(true);
      setIsStarting(false);
    }
  }, [isConnected]);

  // Determine current UI state
  let uiState: UIState;
  if (hasEnded) {
    uiState = 'call-ended';
  } else if (!isConnected && !hasBeenConnectedRef.current) {
    uiState = isStarting ? 'connecting' : 'ready';
  } else if (isConnected) {
    // Agent is in-call: listening, thinking, or speaking
    if (agent.state === 'connecting' || agent.state === 'pre-connect-buffering' || agent.state === 'initializing' || agent.state === 'idle') {
      uiState = 'connecting';
    } else {
      uiState = 'in-call';
    }
  } else {
    uiState = 'ready';
  }

  const isNetworkSlow = localParticipant.connectionQuality === ConnectionQuality.Poor || localParticipant.connectionQuality === ConnectionQuality.Lost;

  const handleStartAgain = useCallback(() => {
    hasBeenConnectedRef.current = false;
    setHasEnded(false);
    setIsStarting(true);
    void Promise.resolve(start()).catch(() => setIsStarting(false));
  }, [start]);

  const handleStartCall = useCallback(() => {
    setIsStarting(true);
    void Promise.resolve(start()).catch(() => setIsStarting(false));
  }, [start]);

  const handleEndCall = useCallback(() => {
    end();
  }, [end]);

  return (
    <AnimatePresence mode="wait">
      {/* Ready state: Welcome view */}
      {uiState === 'ready' && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
        />
      )}

      {/* Connecting state */}
      {uiState === 'connecting' && (
        <ConnectingView
          key="connecting"
          isNetworkSlow={isNetworkSlow}
        />
      )}

      {/* In-call state: Session view */}
      {uiState === 'in-call' && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={appConfig.supportsChatInput}
          supportsVideoInput={appConfig.supportsVideoInput}
          supportsScreenShare={appConfig.supportsScreenShare}
          isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
          audioVisualizerType={appConfig.audioVisualizerType}
          audioVisualizerColor={
            resolvedTheme === 'dark'
              ? appConfig.audioVisualizerColorDark
              : appConfig.audioVisualizerColor
          }
          audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
          audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
          audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
          audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
          audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
          className="fixed inset-0"
        />
      )}

      {/* Call ended state */}
      {uiState === 'call-ended' && (
        <CallEndedView
          key="call-ended"
          onStartAgain={handleStartAgain}
        />
      )}
    </AnimatePresence>
  );
}
