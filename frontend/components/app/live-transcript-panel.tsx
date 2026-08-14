'use client';

import { type ComponentProps, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Clipboard, Globe2, UserRound, Volume2 } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import {
  type AgentState,
  type ReceivedMessage,
  useVoiceAssistant,
} from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';
import { type SchemeResult, SchemeResultCard } from './scheme-result-card';

type TranscriptMessage = {
  id: string;
  text: string;
  fromUser: boolean;
  timestamp: number;
};

const HIGHLIGHT_PATTERN =
  /(PM-KISAN|PM KISAN|MUDRA|PMJDY|Jan Dhan|₹\s?[\d,]+|Rs\.?\s?[\d,]+|रु\.?\s?[\d,]+|next step|अगला कदम)/gi;
const ESCALATION_PATTERN = /(?:reference\s*(?:id|number)?|ref)\s*[:#-]?\s*(#[A-Z]{2,8}-\d{3,})/i;

function highlightText(text: string) {
  return text.split(HIGHLIGHT_PATTERN).map((part, index) =>
    /^(PM-KISAN|PM KISAN|MUDRA|PMJDY|Jan Dhan|₹\s?[\d,]+|Rs\.?\s?[\d,]+|रु\.?\s?[\d,]+|next step|अगला कदम)$/i.test(
      part
    ) ? (
      <mark key={`${part}-${index}`} className="transcript-highlight">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

function schemeResultFor(text: string): SchemeResult | null {
  const normalized = text.toLowerCase();
  const soundsEligible = /eligible|पात्र|qualify|योग्य/.test(normalized);
  if (!soundsEligible) return null;

  if (/pm[ -]?kisan/.test(normalized)) {
    const land = text.match(/(\d+(?:\.\d+)?)\s*(?:hectare|हेक्टेयर)/i)?.[1];
    return {
      scheme: 'PM-KISAN',
      amount: '₹6,000/year · 3 installments',
      detail: land
        ? `आपकी जमीन: ${land} hectares ✓`
        : 'भूमि विवरण की आधिकारिक पुष्टि बाकी है · Official verification required',
      eligible: true,
    };
  }
  if (/mudra/.test(normalized)) {
    return {
      scheme: 'MUDRA',
      amount: 'Business loan guidance',
      detail: 'पात्रता और दस्तावेज़ की बैंक से पुष्टि करें · Verify eligibility at your bank',
      eligible: true,
    };
  }
  return null;
}

function transcriptFromMessages(messages: ReceivedMessage[]): TranscriptMessage[] {
  return messages.map((message) => ({
    id: message.id,
    text: message.message,
    fromUser: message.from?.isLocal === true,
    timestamp: message.timestamp,
  }));
}

interface LiveTranscriptPanelProps extends ComponentProps<'section'> {
  agentState?: AgentState;
  messages: ReceivedMessage[];
}

export function LiveTranscriptPanel({
  agentState,
  messages,
  className,
  ...props
}: LiveTranscriptPanelProps) {
  const { agentTranscriptions } = useVoiceAssistant();
  const [copied, setCopied] = useState(false);
  const [showEscalation, setShowEscalation] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const scrollAnimRef = useRef<number | null>(null);
  const isUserInteractingRef = useRef(false);

  const transcript = useMemo(() => transcriptFromMessages(messages), [messages]);
  const currentCaption = agentTranscriptions.at(-1)?.text?.trim();
  const lastAgentMessage = [...transcript].reverse().find((message) => !message.fromUser)?.text;

  const normaliseForComparison = (value: string) =>
    value.toLocaleLowerCase().replace(/[^\p{L}\p{N}]+/gu, '');
  const hasUncommittedCaption = Boolean(
    currentCaption &&
      (!lastAgentMessage ||
        !normaliseForComparison(lastAgentMessage).includes(normaliseForComparison(currentCaption)))
  );

  const escalationRef = useMemo(() => {
    const source = transcript.map((message) => message.text).join(' ');
    return source.match(ESCALATION_PATTERN)?.[1];
  }, [transcript]);

  const isHindiMode = useMemo(() => {
    const recentMessages = transcript.slice(-3).map((m) => m.text).join(' ') + (currentCaption || '');
    if (!recentMessages) return true;
    const hasDevanagari = /[\u0900-\u097F]/.test(recentMessages);
    return hasDevanagari;
  }, [transcript, currentCaption]);

  const smoothScrollToBottom = useCallback(() => {
    const el = feedRef.current;
    if (!el || isUserInteractingRef.current) return;

    if (scrollAnimRef.current !== null) {
      cancelAnimationFrame(scrollAnimRef.current);
      scrollAnimRef.current = null;
    }

    const start = el.scrollTop;
    const target = el.scrollHeight - el.clientHeight;
    const distance = target - start;

    if (Math.abs(distance) < 2) {
      el.scrollTop = target;
      return;
    }

    const duration = 280; // ms
    const startTime = performance.now();

    const step = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);

      el.scrollTop = start + distance * ease;

      if (progress < 1) {
        scrollAnimRef.current = requestAnimationFrame(step);
      } else {
        el.scrollTop = target;
        scrollAnimRef.current = null;
      }
    };

    scrollAnimRef.current = requestAnimationFrame(step);
  }, []);

  useEffect(() => {
    smoothScrollToBottom();
  }, [transcript.length, currentCaption, smoothScrollToBottom]);

  useEffect(() => {
    return () => {
      if (scrollAnimRef.current !== null) {
        cancelAnimationFrame(scrollAnimRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!escalationRef) return;
    setShowEscalation(true);
    const timeout = window.setTimeout(() => setShowEscalation(false), 4000);
    return () => window.clearTimeout(timeout);
  }, [escalationRef]);

  const copySummary = async () => {
    const summary = transcript
      .slice(-6)
      .map((message) => `${message.fromUser ? 'आप / You' : 'DhanSathi'}: ${message.text}`)
      .join('\n');
    try {
      await navigator.clipboard.writeText(summary || 'DhanSathi call summary');
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section
      className={cn('live-transcript-panel', className)}
      aria-label="बातचीत · Live Transcript"
      {...props}
    >
      <header className="transcript-header">
        <div>
          <p className="text-[15px] font-extrabold text-white">
            बातचीत <span className="text-slate-400">·</span> Live Transcript
          </p>
          <p className="mt-0.5 text-xs text-slate-400">आपकी बातचीत यहाँ दिखेगी</p>
        </div>
        {escalationRef && !showEscalation && (
          <span className="escalation-dot" title={`Human expert alert: ${escalationRef}`} />
        )}
      </header>

      <div className="overflow-hidden px-4 py-0.5">
        <AnimatePresence mode="wait">
          {isHindiMode ? (
            <motion.div
              key="hindi-mode"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="language-banner !m-0 border-amber-500/30 bg-amber-500/10 text-amber-200"
            >
              <Globe2 className="size-3.5 shrink-0" aria-hidden="true" />
              <span>Hindi mode</span>
              <span className="text-slate-300 font-normal">· हिंदी में बात हो रही है</span>
            </motion.div>
          ) : (
            <motion.div
              key="english-mode"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="language-banner !m-0 border-blue-500/30 bg-blue-500/10 text-blue-200"
            >
              <Globe2 className="size-3.5 shrink-0 text-blue-400" aria-hidden="true" />
              <span>English mode</span>
              <span className="text-slate-300 font-normal">· Speaking in English</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {showEscalation && escalationRef && (
        <motion.div
          initial={{ opacity: 0, y: -6, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -6, scale: 0.98 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="escalation-toast"
          role="status"
        >
          🤝 Human expert alert raised <span>· Ref: {escalationRef}</span>
        </motion.div>
      )}

      <div
        ref={feedRef}
        className="transcript-feed"
        role="log"
        aria-live="polite"
        aria-label="Live conversation messages"
        onPointerDown={() => {
          isUserInteractingRef.current = true;
        }}
        onPointerUp={() => {
          setTimeout(() => {
            isUserInteractingRef.current = false;
          }, 600);
        }}
        onTouchStart={() => {
          isUserInteractingRef.current = true;
        }}
        onTouchEnd={() => {
          setTimeout(() => {
            isUserInteractingRef.current = false;
          }, 600);
        }}
      >
        {transcript.length === 0 && !hasUncommittedCaption && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="transcript-empty"
          >
            <Volume2 className="size-5 text-[#F59E0B]" aria-hidden="true" />
            <p>
              बात शुरू होते ही यहाँ शब्द दिखेंगे
              <br />
              <span>Words will appear here as you talk.</span>
            </p>
          </motion.div>
        )}

        <AnimatePresence initial={false}>
          {transcript.map((message) => {
            const result = !message.fromUser ? schemeResultFor(message.text) : null;
            return (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 14, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{
                  duration: 0.18,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className={cn('transcript-message', message.fromUser ? 'from-user' : 'from-agent')}
              >
                <p className="transcript-speaker">
                  {message.fromUser ? (
                    <>
                      <UserRound className="size-3" /> आप <span>· You</span>
                    </>
                  ) : (
                    <>🟡 DhanSathi</>
                  )}
                </p>
                <div className="transcript-bubble">{highlightText(message.text)}</div>
                {result && <SchemeResultCard result={result} />}
              </motion.div>
            );
          })}
        </AnimatePresence>

        <AnimatePresence>
          {agentState === 'speaking' && hasUncommittedCaption && (
            <motion.div
              key="streaming-caption"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 0.85, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
              className="transcript-message from-agent"
              aria-label="DhanSathi is currently speaking"
            >
              <p className="transcript-speaker">🟡 DhanSathi</p>
              <div className="typing-indicator">
                <i />
                <i />
                <i />
                <span className="font-normal text-slate-200">
                  {currentCaption || 'Currently speaking…'}
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <footer className="transcript-footer">
        <button
          type="button"
          onClick={copySummary}
          className="copy-summary-button"
          aria-label="सार कॉपी करें · Copy summary"
        >
          {copied ? <Check className="size-4" /> : <Clipboard className="size-4" />}{' '}
          {copied ? 'कॉपी हो गया · Copied' : 'Copy Summary'}
        </button>
      </footer>
    </section>
  );
}

