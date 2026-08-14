'use client';

import React, { useState } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { AgentStateIndicator } from '@/components/app/agent-state-indicator';
import { LiveTranscriptPanel } from '@/components/app/live-transcript-panel';
import { MobileTranscriptDrawer } from '@/components/app/mobile-transcript-drawer';
import { SafetyNudge } from '@/components/app/safety-nudge';
import { cn } from '@/lib/shadcn/utils';
import { TileLayout } from './tile-view';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  className?: string;
}

export function AgentSessionView_01({
  preConnectMessage = 'सरकारी योजना, बैंकिंग, या धोखाधड़ी के बारे में पूछें · Ask about schemes, banking, or fraud protection',
  supportsChatInput = true,
  supportsVideoInput = true,
  supportsScreenShare = true,
  isPreConnectBufferEnabled = true,

  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerWaveLineWidth,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(false);
  const { state: agentState } = useAgent();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: false,
    screenShare: false,
  };

  return (
    <section
      ref={ref}
      className={cn('dhan-call-surface relative z-10 h-full w-full overflow-hidden', className)}
      {...props}
    >
      <div className="dhan-call-ambient dhan-call-ambient-one" aria-hidden="true" />
      <div className="dhan-call-ambient dhan-call-ambient-two" aria-hidden="true" />
      <div className="dhan-call-grain" aria-hidden="true" />
      <Fade top className="absolute inset-x-4 top-0 z-10 h-40" />

      <div className="absolute inset-x-0 top-6 z-20 flex justify-center md:top-10 md:right-[40%]">
        <AgentStateIndicator />
      </div>
      <SafetyNudge />

      <div className="absolute inset-x-0 top-0 bottom-10 z-0 hidden grid-cols-5 md:grid">
        <div className="relative col-span-3 min-h-0 border-r border-white/10">
          <TileLayout
            contained
            chatOpen={false}
            audioVisualizerType={audioVisualizerType}
            audioVisualizerColor={audioVisualizerColor}
            audioVisualizerColorShift={audioVisualizerColorShift}
            audioVisualizerBarCount={audioVisualizerBarCount}
            audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
            audioVisualizerRadialRadius={audioVisualizerRadialRadius}
            audioVisualizerGridRowCount={audioVisualizerGridRowCount}
            audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
            audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
          />
        </div>
        <LiveTranscriptPanel
          agentState={agentState}
          messages={messages}
          className="col-span-2 h-full rounded-none border-y-0 border-r-0"
        />
      </div>

      <div className="absolute inset-0 z-0 md:hidden">
        <TileLayout
          contained
          chatOpen={false}
          audioVisualizerType={audioVisualizerType}
          audioVisualizerColor={audioVisualizerColor}
          audioVisualizerColorShift={audioVisualizerColorShift}
          audioVisualizerBarCount={audioVisualizerBarCount}
          audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
          audioVisualizerRadialRadius={audioVisualizerRadialRadius}
          audioVisualizerGridRowCount={audioVisualizerGridRowCount}
          audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
          audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
        />
        <MobileTranscriptDrawer
          agentState={agentState}
          messages={messages}
          open={chatOpen}
          onOpenChange={setChatOpen}
        />
      </div>
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:right-[42%] md:left-8"
      >
        {isPreConnectBufferEnabled && (
          <AnimatePresence>
            {messages.length === 0 && (
              <MotionMessage
                key="pre-connect-message"
                duration={2}
                aria-hidden={messages.length > 0}
                {...SHIMMER_MOTION_PROPS}
                className="dhan-conversation-prompt pointer-events-none mx-auto block w-full max-w-sm pb-4 text-center text-sm font-semibold"
              >
                {preConnectMessage}
              </MotionMessage>
            )}
          </AnimatePresence>
        )}
        <div className="relative mx-auto max-w-2xl pb-3 md:pb-12">
          <Fade bottom className="absolute inset-x-0 top-0 h-4 -translate-y-full" />
          <AgentControlBar
            variant="livekit"
            className="dhan-control-dock"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={session.end}
            onIsChatOpenChange={setChatOpen}
            onDeviceError={({ source, error }) => {
              if (source === Track.Source.Microphone) {
                window.dispatchEvent(new CustomEvent('dhan-mic-error', { detail: error }));
              }
            }}
          />
        </div>
      </motion.div>
    </section>
  );
}

