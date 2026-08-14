'use client';

import { ConnectionQuality } from 'livekit-client';
import { AnimatePresence, motion } from 'motion/react';
import { useAgent, useLocalParticipant } from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';


type AgentState =
  | 'disconnected'
  | 'connecting'
  | 'pre-connect-buffering'
  | 'initializing'
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'failed';

function getStateConfig(state: AgentState) {
  switch (state) {
    case 'connecting':
    case 'pre-connect-buffering':
    case 'initializing':
    case 'idle':
      return {
        key: 'connecting',
        label: 'जुड़ रहे हैं… · Connecting…',
        variant: 'connecting' as const,
      };
    case 'listening':
      return {
        key: 'listening',
        label: 'आपको सुन रहे हैं… · Listening to you…',
        variant: 'listening' as const,
      };
    case 'thinking':
      return {
        key: 'thinking',
        label: 'सोच रहे हैं… · Thinking…',
        variant: 'thinking' as const,
      };
    case 'speaking':
      return {
        key: 'speaking',
        label: 'DhanSathi बोल रहा है… · Speaking…',
        variant: 'speaking' as const,
      };
    default:
      return null;
  }
}

function ConnectingIndicator() {
  return (
    <div className="border-primary/30 border-t-primary size-4 animate-spin rounded-full border-2" />
  );
}

function ListeningIndicator() {
  return (
    <span className="relative flex size-3">
      <span className="bg-success absolute inline-flex size-full animate-ping rounded-full opacity-60" />
      <span className="bg-success relative inline-flex size-3 rounded-full" />
    </span>
  );
}

function ThinkingIndicator() {
  return (
    <span className="flex items-center gap-1">
      <span className="bg-primary animate-thinking-dot size-1.5 rounded-full" />
      <span className="bg-primary animate-thinking-dot-delay-1 size-1.5 rounded-full" />
      <span className="bg-primary animate-thinking-dot-delay-2 size-1.5 rounded-full" />
    </span>
  );
}

function SpeakingIndicator() {
  return (
    <span className="flex items-end gap-0.5">
      {[0, 1, 2, 3, 4].map((i) => (
        <span
          key={i}
          className="bg-primary w-[3px] rounded-full"
          style={{
            height: '14px',
            animation: `wave-speaking 1s ease-in-out ${i * 0.1}s infinite`,
          }}
        />
      ))}
    </span>
  );
}

function StateVisual({
  variant,
}: {
  variant: 'connecting' | 'listening' | 'thinking' | 'speaking';
}) {
  switch (variant) {
    case 'connecting':
      return <ConnectingIndicator />;
    case 'listening':
      return <ListeningIndicator />;
    case 'thinking':
      return <ThinkingIndicator />;
    case 'speaking':
      return <SpeakingIndicator />;
  }
}

interface AgentStateIndicatorProps {
  className?: string;
}

export function AgentStateIndicator({ className }: AgentStateIndicatorProps) {
  const agent = useAgent();
  const { localParticipant } = useLocalParticipant();

  const config = getStateConfig(agent.state);

  if (!config) return null;

  return (
    <div className={cn('flex flex-col items-center gap-3', className)}>
      <AnimatePresence mode="wait">
        <motion.div
          key={config.key}
          initial={{ opacity: 0, y: -4, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 4, scale: 0.96 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className={cn('state-badge', `state-badge-${config.variant}`)}
        >
          <StateVisual variant={config.variant} />
          <span className="text-foreground/90 text-xs font-medium md:text-sm">{config.label}</span>
        </motion.div>
      </AnimatePresence>

      {(localParticipant.connectionQuality === ConnectionQuality.Poor ||
        localParticipant.connectionQuality === ConnectionQuality.Lost) && (
        <motion.p
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="slow-connection-pill"
          role="status"
        >
          🔴 Slow connection
        </motion.p>
      )}
    </div>
  );
}
