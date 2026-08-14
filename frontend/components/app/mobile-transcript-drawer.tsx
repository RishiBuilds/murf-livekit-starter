'use client';

import { useState } from 'react';
import { ChevronUp } from 'lucide-react';
import { type PanInfo, motion } from 'motion/react';
import { type AgentState, type ReceivedMessage } from '@livekit/components-react';
import { cn } from '@/lib/shadcn/utils';
import { LiveTranscriptPanel } from './live-transcript-panel';

const SPRING_TRANSITION = {
  type: 'spring' as const,
  damping: 25,
  stiffness: 300,
  mass: 0.85,
};

export function MobileTranscriptDrawer({
  agentState,
  messages,
  open,
  onOpenChange,
}: {
  agentState?: AgentState;
  messages: ReceivedMessage[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const drawerState = !open ? 'closed' : expanded ? 'expanded' : 'half';

  const drawerVariants = {
    closed: { height: '4.25rem' },
    half: { height: '45svh' },
    expanded: { height: '82svh' },
  };

  const handleDragEnd = (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    const { offset, velocity } = info;

    if (velocity.y < -300 || offset.y < -40) {
      if (!open) {
        onOpenChange(true);
        setExpanded(false);
      } else if (!expanded) {
        setExpanded(true);
      }
      return;
    }

    if (velocity.y > 300 || offset.y > 40) {
      if (expanded) {
        setExpanded(false);
      } else if (open) {
        onOpenChange(false);
      }
      return;
    }
  };

  const handleToggle = () => {
    if (!open) {
      onOpenChange(true);
      setExpanded(false);
    } else if (!expanded) {
      setExpanded(true);
    } else {
      setExpanded(false);
      onOpenChange(false);
    }
  };

  return (
    <motion.aside
      className="mobile-transcript-drawer md:hidden"
      initial="closed"
      animate={drawerState}
      variants={drawerVariants}
      transition={SPRING_TRANSITION}
    >
      <motion.div
        drag="y"
        dragConstraints={{ top: 0, bottom: 0 }}
        dragElastic={0.18}
        onDragEnd={handleDragEnd}
        onClick={handleToggle}
        className="drawer-handle cursor-pointer active:cursor-grabbing"
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-label="बातचीत देखें · View transcript"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggle();
          }
        }}
      >
        <span className="drawer-grip" aria-hidden="true" />
        <span className="flex items-center gap-1">
          बातचीत देखें <span className="text-slate-400">· View Transcript</span>
        </span>
        <ChevronUp
          className={cn(
            'size-4 transition-transform duration-300 ease-out',
            expanded && 'rotate-180',
            !open && 'opacity-60'
          )}
        />
      </motion.div>
      {open && (
        <div className="h-[calc(100%-4.25rem)] overflow-hidden">
          <LiveTranscriptPanel
            agentState={agentState}
            messages={messages}
            className="h-full rounded-none border-0"
          />
        </div>
      )}
    </motion.aside>
  );
}

