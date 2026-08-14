'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { ConnectionQuality } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import {
  useAgent,
  useLocalParticipant,
  useSessionContext,
  useSessionMessages,
} from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { Button } from '@/components/ui/button';
import { type CallRecap, createCallRecap } from '@/lib/call-recap';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
    },
    hidden: {
      opacity: 0,
      y: 8,
      scale: 0.995,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.28,
    ease: [0.16, 1, 0.3, 1],
  },
};

function ConnectingView({ isNetworkSlow }: { isNetworkSlow: boolean }) {
  return (
    <motion.div
      key="connecting"
      {...VIEW_MOTION_PROPS}
      className="bg-background flex min-h-svh flex-col items-center justify-center overflow-y-auto px-6 py-8 text-center"
    >
      <div className="connecting-orb mb-6">
        <div className="connecting-orb-ring" />
        <div className="connecting-orb-core">
          <span className="text-lg font-black">₹</span>
        </div>
      </div>

      <p className="text-foreground text-base font-semibold">DhanSathi से जुड़ रहे हैं…</p>
      <p className="text-muted-foreground mt-1 text-sm">Connecting to DhanSathi…</p>

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

function CallEndedView({ recap, onStartAgain }: { recap: CallRecap; onStartAgain: () => void }) {
  const listenToRecap = () => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(
      `${recap.topic}. ${recap.outcome} ${recap.nextStep}`
    );
    utterance.lang = 'en-IN';
    window.speechSynthesis.speak(utterance);
  };

  const shareSummary = async () => {
    const text = [
      'DhanSathi · आज का सार / Call recap',
      recap.topic,
      recap.outcome,
      `अगला कदम / Next step: ${recap.nextStep}`,
      recap.escalationRef ? `Human support ref: ${recap.escalationRef}` : '',
    ]
      .filter(Boolean)
      .join('\n');
    try {
      if (navigator.share) await navigator.share({ title: 'DhanSathi Call Recap', text });
      else await navigator.clipboard.writeText(text);
    } catch {
    }
  };

  return (
    <motion.div
      key="call-ended"
      {...VIEW_MOTION_PROPS}
      className="bg-background flex min-h-svh flex-col items-center justify-center overflow-y-auto px-6 py-8 text-center"
    >
      <motion.div
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="bg-success/10 mb-6 flex size-16 items-center justify-center rounded-full"
      >
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
      </motion.div>

      <h2 className="text-foreground text-lg font-bold md:text-xl">बातचीत समाप्त हुई</h2>
      <p className="text-muted-foreground mt-1 text-sm">Conversation ended</p>

      <p className="text-muted-foreground mt-4 max-w-sm text-xs leading-5 md:text-sm">
        DhanSathi से बात करने के लिए धन्यवाद। क्या आप कुछ और जानना चाहते हैं?
        <br />
        <span className="text-muted-foreground/70">
          Thanks for talking to DhanSathi. Would you like to know more?
        </span>
      </p>

      <section className="recap-card mt-5 w-full max-w-sm p-4 text-left">
        <p className="text-success text-xs font-extrabold tracking-wide uppercase">
          Aaj ka saar · Call recap
        </p>
        <p className="mt-2 text-sm font-bold">{recap.topic}</p>
        <p className="text-muted-foreground mt-1 text-xs leading-5">{recap.outcome}</p>
        <div className="border-primary/20 bg-primary/8 mt-3 rounded-xl border px-3 py-2.5">
          <p className="text-xs font-bold">Agla kadam · Next step</p>
          <p className="text-muted-foreground mt-1 text-xs leading-5">{recap.nextStep}</p>
        </div>
        {recap.eligibleSchemes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {recap.eligibleSchemes.map((scheme) => (
              <span
                key={scheme}
                className="border-success/30 bg-success/10 text-success rounded-full border px-2 py-1 text-[11px] font-bold"
              >
                ✓ {scheme}
              </span>
            ))}
          </div>
        )}
        {recap.escalationRef && (
          <p className="border-success/25 bg-success/10 text-success mt-3 rounded-lg border px-2.5 py-2 text-xs font-bold">
            🤝 Human expert alert · Ref: {recap.escalationRef}
          </p>
        )}
        {recap.transcriptExcerpt.length > 0 && (
          <details className="mt-3 rounded-xl border border-white/10 bg-black/10 px-3 py-2">
            <summary className="text-foreground cursor-pointer text-xs font-bold">
              हाल की बातचीत · Last exchanges
            </summary>
            <div className="text-muted-foreground mt-2 space-y-1.5 text-xs leading-5">
              {recap.transcriptExcerpt.map((message, index) => (
                <p key={`${message.text}-${index}`}>
                  <span className="text-foreground font-bold">
                    {message.fromUser ? 'आप / You' : 'DhanSathi'}:{' '}
                  </span>
                  {message.text}
                </p>
              ))}
            </div>
          </details>
        )}
        <div className="mt-3 flex gap-1">
          <Button variant="ghost" size="sm" onClick={listenToRecap} className="-ml-2 text-xs">
            🔊 Listen to recap
          </Button>
          <Button variant="ghost" size="sm" onClick={shareSummary} className="text-xs">
            📤 Share Summary
          </Button>
        </div>
      </section>

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

type UIState = 'ready' | 'connecting' | 'in-call' | 'call-ended';

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const session = useSessionContext();
  const { isConnected, start, end } = session;
  const agent = useAgent();
  const { resolvedTheme } = useTheme();
  const { localParticipant } = useLocalParticipant();
  const { messages } = useSessionMessages(session);

  const hasBeenConnectedRef = useRef(false);
  const [hasEnded, setHasEnded] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const recapRef = useRef<CallRecap>(createCallRecap([]));

  useEffect(() => {
    if (messages.length > 0) {
      recapRef.current = createCallRecap(messages);
    }
  }, [messages]);

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

  let uiState: UIState;
  if (hasEnded) {
    uiState = 'call-ended';
  } else if (!isConnected && !hasBeenConnectedRef.current) {
    uiState = isStarting ? 'connecting' : 'ready';
  } else if (isConnected) {
    if (
      agent.state === 'connecting' ||
      agent.state === 'pre-connect-buffering' ||
      agent.state === 'initializing' ||
      agent.state === 'idle'
    ) {
      uiState = 'connecting';
    } else {
      uiState = 'in-call';
    }
  } else {
    uiState = 'ready';
  }

  const isNetworkSlow =
    localParticipant.connectionQuality === ConnectionQuality.Poor ||
    localParticipant.connectionQuality === ConnectionQuality.Lost;

  const handleStartAgain = useCallback(() => {
    hasBeenConnectedRef.current = false;
    setHasEnded(false);
    setIsStarting(true);
    recapRef.current = createCallRecap([]);
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
      {uiState === 'ready' && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          onStartCall={handleStartCall}
        />
      )}

      {uiState === 'connecting' && (
        <ConnectingView key="connecting" isNetworkSlow={isNetworkSlow} />
      )}

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

      {uiState === 'call-ended' && (
        <CallEndedView key="call-ended" recap={recapRef.current} onStartAgain={handleStartAgain} />
      )}
    </AnimatePresence>
  );
}
