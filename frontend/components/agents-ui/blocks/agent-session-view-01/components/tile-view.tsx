import React, { useEffect, useMemo, useState } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import {
  type TrackReference,
  VideoTrack,
  useAgent,
  useLocalParticipant,
  useMultibandTrackVolume,
  useTrackVolume,
  useTracks,
  useVoiceAssistant,
} from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';
import { AudioVisualizer } from './audio-visualizer';

const ANIMATION_TRANSITION: MotionProps['transition'] = {
  type: 'spring',
  stiffness: 675,
  damping: 75,
  mass: 1,
};

function DhanSathiAvatar({ state }: { state: string }) {
  const { audioTrack } = useVoiceAssistant();
  const rawVolume = useTrackVolume(audioTrack);
  const bands = useMultibandTrackVolume(audioTrack, { bands: 5 });

  const isSpeaking = state === 'speaking';
  const isListening = state === 'listening';
  const isThinking = state === 'thinking';

  // Smooth volume for speech lip-sync (0.0 to 1.0)
  const volume = isSpeaking ? Math.min(1, Math.max(0, rawVolume)) : 0;

  // Natural blinking effect (blinks every ~3.5s for 140ms)
  const [isBlinking, setIsBlinking] = useState(false);
  useEffect(() => {
    const blinkTimer = setInterval(
      () => {
        setIsBlinking(true);
        setTimeout(() => setIsBlinking(false), 140);
      },
      3200 + Math.random() * 1500
    );

    return () => clearInterval(blinkTimer);
  }, []);

  // Calculate dynamic mouth opening height (px)
  const mouthOpen = isSpeaking ? Math.min(22, Math.max(3, volume * 32)) : 2;
  const upperLipY = 89 - mouthOpen * 0.15;
  const lowerLipY = 89 + mouthOpen;

  return (
    <div
      className={cn(
        'dhan-avatar',
        isSpeaking && 'dhan-avatar-speaking',
        isListening && 'dhan-avatar-listening',
        isThinking && 'dhan-avatar-thinking'
      )}
      aria-label="DhanSathi voice assistant avatar"
      role="img"
    >
      <span className="dhan-avatar-orbit dhan-avatar-orbit-one" aria-hidden="true" />
      <span className="dhan-avatar-orbit dhan-avatar-orbit-two" aria-hidden="true" />
      <span className="dhan-avatar-orbit dhan-avatar-orbit-three" aria-hidden="true" />
      {/* Audio-reactive Halo Glow */}
      <span
        className="dhan-avatar-halo"
        style={{
          transform: isSpeaking ? `scale(${1 + volume * 0.3})` : undefined,
          opacity: isSpeaking ? 0.75 + volume * 0.25 : undefined,
        }}
      />

      {/* Dynamic Soundbars flanking portrait */}
      <div className="dhan-avatar-eq-bars left" aria-hidden="true">
        {[0, 1, 2].map((i) => {
          const val = isSpeaking && bands[i] ? Math.max(0.18, bands[i]) : 0.18;
          return (
            <span
              key={i}
              className="dhan-eq-bar"
              style={{
                height: `${val * 22 + 4}px`,
                opacity: isSpeaking ? 0.85 : 0.25,
              }}
            />
          );
        })}
      </div>

      <div className="dhan-avatar-eq-bars right" aria-hidden="true">
        {[2, 1, 0].map((i) => {
          const val = isSpeaking && bands[i] ? Math.max(0.18, bands[i]) : 0.18;
          return (
            <span
              key={i}
              className="dhan-eq-bar"
              style={{
                height: `${val * 22 + 4}px`,
                opacity: isSpeaking ? 0.85 : 0.25,
              }}
            />
          );
        })}
      </div>

      {/* Main Avatar Frame */}
      <div
        className="dhan-avatar-frame"
        style={{
          transform: isSpeaking ? `rotate(-2deg) scale(${1 + volume * 0.04})` : undefined,
        }}
      >
        <svg viewBox="0 0 160 160" aria-hidden="true">
          <defs>
            <linearGradient id="faceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#f7c8a4" />
              <stop offset="100%" stopColor="#e5ad80" />
            </linearGradient>
            <linearGradient id="scarfGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#2563eb" />
              <stop offset="100%" stopColor="#1d4ed8" />
            </linearGradient>
            <linearGradient id="hairGrad" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#2b2826" />
              <stop offset="100%" stopColor="#141211" />
            </linearGradient>
            <filter id="goldGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow
                dx="0"
                dy="1"
                stdDeviation="1.5"
                floodColor="#f5a623"
                floodOpacity="0.7"
              />
            </filter>
          </defs>

          {/* Scarf / Dupatta */}
          <path
            className="dhan-avatar-scarf"
            fill="url(#scarfGrad)"
            d="M30 152c5-34 22-48 50-48s45 14 50 48H30Z"
          />

          {/* Back Hair */}
          <path
            className="dhan-avatar-hair"
            fill="url(#hairGrad)"
            d="M44 73c0-33 16-52 36-52 24 0 40 19 36 55l-11 12-57-1-4-14Z"
          />

          {/* Face Base */}
          <ellipse
            className="dhan-avatar-face"
            fill="url(#faceGrad)"
            cx="80"
            cy="76"
            rx="29"
            ry="35"
          />

          {/* Front Hair Style */}
          <path
            className="dhan-avatar-hair"
            fill="url(#hairGrad)"
            d="M48 64c3-29 19-42 35-42 17 0 31 12 35 32-9-7-20-12-34-12-15 0-27 8-36 22Z"
          />

          {/* Gold Jhumka Earrings */}
          <circle cx="48" cy="82" r="3" fill="#f5a623" filter="url(#goldGlow)" />
          <path d="M 46 85 L 50 85 L 48 89 Z" fill="#f5a623" />
          <circle cx="112" cy="82" r="3" fill="#f5a623" filter="url(#goldGlow)" />
          <path d="M 110 85 L 114 85 L 112 89 Z" fill="#f5a623" />

          {/* Eyebrows (react to agent state) */}
          <path
            className="dhan-avatar-eyebrow"
            d={
              isListening
                ? 'M 61 67 Q 69 63 77 67'
                : isThinking
                  ? 'M 61 65 Q 69 67 77 64'
                  : 'M 61 66 Q 69 63 77 66'
            }
            stroke="#2b2826"
            strokeWidth="2.2"
            strokeLinecap="round"
            fill="none"
          />
          <path
            className="dhan-avatar-eyebrow"
            d={
              isListening
                ? 'M 83 67 Q 91 63 99 67'
                : isThinking
                  ? 'M 83 63 Q 91 66 99 65'
                  : 'M 83 66 Q 91 63 99 66'
            }
            stroke="#2b2826"
            strokeWidth="2.2"
            strokeLinecap="round"
            fill="none"
          />

          {/* Eyes with Natural Blinking */}
          <g
            transform={isBlinking ? 'scale(1, 0.1)' : 'scale(1, 1)'}
            style={{ transformOrigin: '80px 74px' }}
          >
            <ellipse cx="69" cy="74" rx="3.5" ry="4" fill="#ffffff" />
            <circle
              cx={isThinking ? 70.5 : 69}
              cy={isThinking ? 72.5 : 74}
              r="2.4"
              fill="#1e1b18"
            />
            <circle
              cx={isThinking ? 71.3 : 70}
              cy={isThinking ? 71.7 : 73}
              r="0.8"
              fill="#ffffff"
            />

            <ellipse cx="91" cy="74" rx="3.5" ry="4" fill="#ffffff" />
            <circle
              cx={isThinking ? 92.5 : 91}
              cy={isThinking ? 72.5 : 74}
              r="2.4"
              fill="#1e1b18"
            />
            <circle
              cx={isThinking ? 93.3 : 92}
              cy={isThinking ? 71.7 : 73}
              r="0.8"
              fill="#ffffff"
            />
          </g>

          {/* Traditional Crimson Bindi */}
          <circle className="dhan-avatar-bindi" cx="80" cy="60" r="2" fill="#d92d20" />

          {/* Nose Accent */}
          <path
            d="M 79 74 Q 81 79 78 81"
            stroke="#d49466"
            strokeWidth="1.5"
            strokeLinecap="round"
            fill="none"
          />

          {/* Dynamic Audio-Reactive Mouth */}
          {isSpeaking && mouthOpen > 3 ? (
            <g className="dhan-avatar-mouth-speaking">
              {/* Mouth Interior */}
              <path
                d={`M 68 89 Q 80 ${upperLipY} 92 89 Q 80 ${lowerLipY} 68 89 Z`}
                fill="#6b1d2f"
              />
              {/* Upper Teeth Line */}
              <path
                d={`M 72 89 Q 80 89 88 89 L 87 ${89 + Math.min(4, mouthOpen * 0.35)} Q 80 ${89 + Math.min(4, mouthOpen * 0.35)} 73 ${89 + Math.min(4, mouthOpen * 0.35)} Z`}
                fill="#ffffff"
                opacity="0.9"
              />
              {/* Tongue Accent */}
              {mouthOpen > 8 && (
                <path
                  d={`M 73 ${lowerLipY - 2} Q 80 ${lowerLipY - Math.min(7, mouthOpen * 0.4)} 87 ${lowerLipY - 2} Z`}
                  fill="#e57373"
                />
              )}
              {/* Lip Outlines */}
              <path
                d={`M 68 89 Q 80 ${upperLipY} 92 89`}
                stroke="#c95a63"
                strokeWidth="1.8"
                strokeLinecap="round"
                fill="none"
              />
              <path
                d={`M 68 89 Q 80 ${lowerLipY} 92 89`}
                stroke="#b5434d"
                strokeWidth="1.8"
                strokeLinecap="round"
                fill="none"
              />
            </g>
          ) : (
            /* Friendly Gentle Smile when idle/listening */
            <path
              className="dhan-avatar-smile"
              d="M 70 90 Q 80 96 90 90"
              stroke="#b5434d"
              strokeWidth="2.4"
              strokeLinecap="round"
              fill="none"
            />
          )}

          {/* Cheeks Warm Blush */}
          <ellipse cx="61" cy="80" rx="4.5" ry="2.5" fill="#f48fb1" opacity="0.4" />
          <ellipse cx="99" cy="80" rx="4.5" ry="2.5" fill="#f48fb1" opacity="0.4" />
        </svg>
      </div>

      {/* Avatar Name Tag */}
      <span className="dhan-avatar-name flex items-center gap-1.5">DhanSathi</span>

      {/* Avatar Status Badge with Live Waveform */}
      <span className="dhan-avatar-status flex items-center gap-1.5">
        {isSpeaking ? (
          <>
            <span className="flex h-3 items-end gap-0.5">
              <span
                className="bg-primary animate-wave-speaking w-0.5 rounded-full"
                style={{ height: '80%' }}
              />
              <span
                className="bg-primary animate-wave-speaking w-0.5 rounded-full"
                style={{ height: '100%', animationDelay: '0.2s' }}
              />
              <span
                className="bg-primary animate-wave-speaking w-0.5 rounded-full"
                style={{ height: '60%', animationDelay: '0.4s' }}
              />
            </span>
            <span>Speaking...</span>
          </>
        ) : isListening ? (
          <>
            <span className="bg-success size-1.5 animate-ping rounded-full" />
            <span>Listening to you</span>
          </>
        ) : isThinking ? (
          <>
            <span className="bg-primary size-1.5 animate-pulse rounded-full" />
            <span>Thinking...</span>
          </>
        ) : (
          <span>Here to help</span>
        )}
      </span>
    </div>
  );
}

const tileViewClassNames = {
  // GRID
  // 2 Columns x 3 Rows
  grid: [
    'h-full w-full',
    'grid gap-x-2 place-content-center',
    'grid-cols-[1fr_1fr] grid-rows-[90px_1fr_90px]',
  ],
  // Agent
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 1 / Row 1
  // align: x-end y-center
  agentChatOpenWithSecondTile: ['col-start-1 row-start-1', 'self-center justify-self-end'],
  // Agent
  // chatOpen: true,
  // hasSecondTile: false
  // layout: Column 1 / Row 1 / Column-Span 2
  // align: x-center y-center
  agentChatOpenWithoutSecondTile: ['col-start-1 row-start-1', 'col-span-2', 'place-content-center'],
  // Agent
  // chatOpen: false
  // layout: Column 1 / Row 1 / Column-Span 2 / Row-Span 3
  // align: x-center y-center
  agentChatClosed: ['col-start-1 row-start-1', 'col-span-2 row-span-3', 'place-content-center'],
  // Second tile
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 2 / Row 1
  // align: x-start y-center
  secondTileChatOpen: ['col-start-2 row-start-1', 'self-center justify-self-start'],
  // Second tile
  // chatOpen: false,
  // hasSecondTile: false
  // layout: Column 2 / Row 2
  // align: x-end y-end
  secondTileChatClosed: ['col-start-2 row-start-3', 'place-content-end'],
};

export function useLocalTrackRef(source: Track.Source) {
  const { localParticipant } = useLocalParticipant();
  const publication = localParticipant.getTrackPublication(source);
  const trackRef = useMemo<TrackReference | undefined>(
    () => (publication ? { source, participant: localParticipant, publication } : undefined),
    [source, publication, localParticipant]
  );
  return trackRef;
}

interface TileLayoutProps {
  chatOpen: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerWaveLineWidth?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerBarCount?: number;
}

export function TileLayout({
  chatOpen,
  audioVisualizerType,
  audioVisualizerColor,
  audioVisualizerColorShift,
  audioVisualizerBarCount,
  audioVisualizerRadialBarCount,
  audioVisualizerRadialRadius,
  audioVisualizerGridRowCount,
  audioVisualizerGridColumnCount,
  audioVisualizerWaveLineWidth,
}: TileLayoutProps) {
  const { videoTrack: agentVideoTrack } = useVoiceAssistant();
  const { state: agentState } = useAgent();
  const [screenShareTrack] = useTracks([Track.Source.ScreenShare]);
  const cameraTrack: TrackReference | undefined = useLocalTrackRef(Track.Source.Camera);

  const isCameraEnabled = cameraTrack && !cameraTrack.publication.isMuted;
  const isScreenShareEnabled = screenShareTrack && !screenShareTrack.publication.isMuted;
  const hasSecondTile = isCameraEnabled || isScreenShareEnabled;

  const animationDelay = chatOpen ? 0 : 0.15;
  const isAvatar = agentVideoTrack !== undefined;
  const videoWidth = agentVideoTrack?.publication.dimensions?.width ?? 0;
  const videoHeight = agentVideoTrack?.publication.dimensions?.height ?? 0;

  return (
    <div className="absolute inset-x-0 top-8 bottom-32 z-50 md:top-12 md:bottom-40">
      <div className="relative mx-auto h-full max-w-2xl px-4 md:px-0">
        <div className={cn(tileViewClassNames.grid)}>
          {/* Agent */}
          <div
            className={cn([
              'grid',
              !chatOpen && tileViewClassNames.agentChatClosed,
              chatOpen && hasSecondTile && tileViewClassNames.agentChatOpenWithSecondTile,
              chatOpen && !hasSecondTile && tileViewClassNames.agentChatOpenWithoutSecondTile,
            ])}
          >
            <AnimatePresence mode="popLayout">
              {!isAvatar && (
                // Audio Agent
                <motion.div
                  key="agent"
                  layoutId="agent"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{
                    ...ANIMATION_TRANSITION,
                    delay: animationDelay,
                  }}
                  className={cn('relative aspect-square h-[214px] sm:h-[250px]')}
                >
                  <AudioVisualizer
                    key="audio-visualizer"
                    initial={{ scale: 1 }}
                    animate={{ scale: chatOpen ? 0.2 : 1 }}
                    transition={{
                      ...ANIMATION_TRANSITION,
                      delay: animationDelay,
                    }}
                    audioVisualizerType={audioVisualizerType}
                    audioVisualizerColor={audioVisualizerColor}
                    audioVisualizerColorShift={audioVisualizerColorShift}
                    audioVisualizerBarCount={audioVisualizerBarCount}
                    audioVisualizerRadialBarCount={audioVisualizerRadialBarCount}
                    audioVisualizerRadialRadius={audioVisualizerRadialRadius}
                    audioVisualizerGridRowCount={audioVisualizerGridRowCount}
                    audioVisualizerGridColumnCount={audioVisualizerGridColumnCount}
                    audioVisualizerWaveLineWidth={audioVisualizerWaveLineWidth}
                    isChatOpen={chatOpen}
                    className={cn(
                      'absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2',
                      'bg-background/30 rounded-[50px] border border-transparent opacity-80 transition-[border,drop-shadow]',
                      chatOpen && 'border-input shadow-2xl/10 delay-200'
                    )}
                    style={{ color: audioVisualizerColor }}
                  />
                  <DhanSathiAvatar state={agentState} />
                </motion.div>
              )}

              {isAvatar && (
                // Avatar Agent
                <motion.div
                  key="avatar"
                  layoutId="avatar"
                  initial={{
                    scale: 1,
                    opacity: 1,
                    maskImage:
                      'radial-gradient(circle, rgba(0, 0, 0, 1) 0, rgba(0, 0, 0, 1) 20px, transparent 20px)',
                    filter: 'blur(20px)',
                  }}
                  animate={{
                    maskImage:
                      'radial-gradient(circle, rgba(0, 0, 0, 1) 0, rgba(0, 0, 0, 1) 500px, transparent 500px)',
                    filter: 'blur(0px)',
                    borderRadius: chatOpen ? 6 : 12,
                  }}
                  transition={{
                    ...ANIMATION_TRANSITION,
                    delay: animationDelay,
                    maskImage: {
                      duration: 1,
                    },
                    filter: {
                      duration: 1,
                    },
                  }}
                  className={cn(
                    'overflow-hidden bg-black drop-shadow-xl/80',
                    chatOpen ? 'h-[90px]' : 'h-auto w-full'
                  )}
                >
                  <VideoTrack
                    width={videoWidth}
                    height={videoHeight}
                    trackRef={agentVideoTrack}
                    className={cn(chatOpen && 'size-[90px] object-cover')}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div
            className={cn([
              'grid',
              chatOpen && tileViewClassNames.secondTileChatOpen,
              !chatOpen && tileViewClassNames.secondTileChatClosed,
            ])}
          >
            {/* Camera & Screen Share */}
            <AnimatePresence>
              {((cameraTrack && isCameraEnabled) || (screenShareTrack && isScreenShareEnabled)) && (
                <motion.div
                  key="camera"
                  layout="position"
                  layoutId="camera"
                  initial={{
                    opacity: 0,
                    scale: 0,
                  }}
                  animate={{
                    opacity: 1,
                    scale: 1,
                  }}
                  exit={{
                    opacity: 0,
                    scale: 0,
                  }}
                  transition={{
                    ...ANIMATION_TRANSITION,
                    delay: animationDelay,
                  }}
                  className="aspect-square size-[90px] drop-shadow-lg/20"
                >
                  <VideoTrack
                    trackRef={cameraTrack || screenShareTrack}
                    width={(cameraTrack || screenShareTrack)?.publication.dimensions?.width ?? 0}
                    height={(cameraTrack || screenShareTrack)?.publication.dimensions?.height ?? 0}
                    className="bg-muted aspect-square size-[90px] rounded-md object-cover"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
