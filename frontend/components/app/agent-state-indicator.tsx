'use client';

import { useAgent, useVoiceAssistant } from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';

/**
 * Agent state values from useAgent(), defined locally since the type
 * isn't reliably re-exported from the package's main barrel.
 */
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

/**
 * Map AgentState to user-facing state config
 */
function getStateConfig(state: AgentState) {
  switch (state) {
    case 'connecting':
    case 'pre-connect-buffering':
    case 'initializing':
    case 'idle':
      return {
        label: 'जुड़ रहे हैं… · Connecting…',
        variant: 'connecting' as const,
      };
    case 'listening':
      return {
        label: 'आपको सुन रहे हैं… · Listening to you…',
        variant: 'listening' as const,
      };
    case 'thinking':
      return {
        label: 'सोच रहे हैं… · Thinking…',
        variant: 'thinking' as const,
      };
    case 'speaking':
      return {
        label: 'DhanSathi बोल रहा है… · Speaking…',
        variant: 'speaking' as const,
      };
    default:
      return null;
  }
}

/**
 * Connecting indicator: amber spinning ring
 */
function ConnectingIndicator() {
  return (
    <div className="border-primary/30 border-t-primary size-4 animate-spin rounded-full border-2" />
  );
}

/**
 * Listening indicator: pulsing green dot
 */
function ListeningIndicator() {
  return (
    <span className="relative flex size-3">
      <span className="bg-success absolute inline-flex size-full animate-ping rounded-full opacity-60" />
      <span className="bg-success relative inline-flex size-3 rounded-full" />
    </span>
  );
}

/**
 * Thinking indicator: three amber dots with staggered animation
 */
function ThinkingIndicator() {
  return (
    <span className="flex items-center gap-1">
      <span className="bg-primary animate-thinking-dot size-1.5 rounded-full" />
      <span className="bg-primary animate-thinking-dot-delay-1 size-1.5 rounded-full" />
      <span className="bg-primary animate-thinking-dot-delay-2 size-1.5 rounded-full" />
    </span>
  );
}

/**
 * Speaking indicator: animated golden wave bars
 */
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

/**
 * Visual indicator for the variant
 */
function StateVisual({ variant }: { variant: 'connecting' | 'listening' | 'thinking' | 'speaking' }) {
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

/**
 * AgentStateIndicator shows current state as a badge plus live captions strip.
 *
 * Uses:
 * - `useAgent()` for the state value
 * - `useVoiceAssistant().agentTranscriptions` for real-time streaming captions
 */
export function AgentStateIndicator({ className }: AgentStateIndicatorProps) {
  const agent = useAgent();
  const { agentTranscriptions } = useVoiceAssistant();

  const config = getStateConfig(agent.state);

  if (!config) return null;

  // Get the latest transcription text for the captions strip
  const latestTranscription = agentTranscriptions.length > 0
    ? agentTranscriptions[agentTranscriptions.length - 1]
    : null;

  return (
    <div className={cn('flex flex-col items-center gap-3', className)}>
      {/* State badge */}
      <div className="state-badge">
        <StateVisual variant={config.variant} />
        <span className="text-foreground/80 text-xs font-medium md:text-sm">
          {config.label}
        </span>
      </div>

      {/* Live captions strip, visible when agent is speaking or thinking */}
      {latestTranscription && (config.variant === 'speaking' || config.variant === 'thinking') && (
        <div className="bg-background/60 border-border/30 mx-auto max-w-md rounded-lg border px-4 py-2 text-center backdrop-blur-sm">
          <p className="text-foreground/70 text-xs leading-relaxed md:text-sm">
            {latestTranscription.text}
          </p>
        </div>
      )}
    </div>
  );
}
