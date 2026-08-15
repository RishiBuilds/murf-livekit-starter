import {
  ArrowUpRight,
  BadgeIndianRupee,
  BarChart3,
  Headphones,
  Landmark,
  Lock,
  Mic,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const features = [
  { icon: Landmark, title: 'Yojana dekhein', copy: 'Check PM-KISAN, pension and housing schemes' },
  {
    icon: BadgeIndianRupee,
    title: 'Banking mein madad',
    copy: 'Simple help with UPI, KYC and accounts',
  },
  { icon: ShieldCheck, title: 'Fraud se bachein', copy: 'OTP, UPI and scam safety support' },
];

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => (
  <div ref={ref} className="landing-shell min-h-svh overflow-hidden px-4 py-5 sm:px-6">
    <div className="tricolour-bar" aria-hidden="true" />
    <div className="landing-glow landing-glow-one" />
    <div className="landing-glow landing-glow-two" />
    <div className="landing-grid" />
    <section className="relative mx-auto flex min-h-[calc(100svh-2.5rem)] w-full max-w-6xl flex-col justify-between">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="brand-mark">
            <span>₹</span>
          </div>
          <div>
            <p className="text-sm font-extrabold tracking-tight">DhanSathi</p>
            <p className="text-muted-foreground text-[10px] font-semibold tracking-[0.14em] uppercase">
              Financial companion
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <a
            href="/analytics"
            target="_blank"
            rel="noopener noreferrer"
            className="header-pill header-pill-emerald"
          >
            <BarChart3 size={14} />
            <span className="hidden sm:inline">Call Analytics</span>
          </a>
          <a
            href="/escalations"
            target="_blank"
            rel="noopener noreferrer"
            className="header-pill header-pill-indigo"
          >
            <Headphones size={14} />
            <span className="hidden sm:inline">Open Escalations</span>
          </a>
          <div className="language-pill">
            हिंदी <span>•</span> ENG
          </div>
          <div className="online-pill">
            <span className="online-dot" />
            Available
          </div>
        </div>
      </div>
      <div className="landing-hero mx-auto grid w-full max-w-5xl items-center gap-10 py-8 lg:grid-cols-[1fr_0.84fr] lg:gap-16">
        <div className="flex flex-col items-center text-center lg:items-start lg:text-left">
          <div className="eyebrow">
            <Sparkles size={14} />
            Your AI financial companion
          </div>
          <h1 className="mt-5 max-w-2xl text-4xl font-black tracking-[-0.055em] text-balance sm:text-5xl md:text-6xl">
            Guidance that feels like <span className="text-gradient">a conversation.</span>
          </h1>
          <p className="text-muted-foreground mt-5 max-w-xl text-sm leading-6 sm:text-base sm:leading-7">
            सरकारी योजनाएँ, banking help और fraud safety. बस बोलिए। Get clear, practical answers in
            simple Hindi or English.
          </p>
          <Button
            size="lg"
            onClick={onStartCall}
            className="start-call-button group mt-8 h-14 w-full max-w-sm rounded-2xl text-sm font-extrabold sm:text-base"
          >
            <span className="flex items-center gap-2">
              <Mic size={18} fill="currentColor" />
              {startButtonText}
            </span>
            <ArrowUpRight
              className="transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
              size={19}
            />
          </Button>
          <div className="landing-safety-note mt-4 max-w-sm text-left">
            <ShieldCheck size={16} />
            <span>
              <strong>Private by design.</strong> DhanSathi never asks for your OTP, PIN, or money.
            </span>
          </div>
          <div className="trust-row mt-6 lg:justify-start">
            <span className="trust-item">
              <Lock size={13} /> Free &amp; secure
            </span>
            <span className="trust-item">
              <Sparkles size={13} /> Hindi + English
            </span>
            <span className="trust-item">
              <Mic size={13} /> Just talk
            </span>
          </div>
        </div>

        <div className="landing-preview" aria-label="DhanSathi voice session preview">
          <div className="landing-preview-status">
            <span className="online-dot" /> DhanSathi is ready
            <span>Secure voice session</span>
          </div>
          <div className="landing-wave" aria-hidden="true">
            {Array.from({ length: 33 }, (_, index) => (
              <i key={index} style={{ '--delay': `${index * 45}ms` } as React.CSSProperties} />
            ))}
          </div>
          <div className="landing-agent-label">
            <span className="landing-agent-icon">₹</span>
            <span>
              <strong>DhanSathi</strong>
              <small>Financial companion · Hindi + English</small>
            </span>
          </div>
          <div className="landing-conversation-card">
            <p className="landing-speaker you">You</p>
            <p>मुझे PM-KISAN के बारे में जानना है।</p>
            <p className="landing-speaker agent">DhanSathi</p>
            <p>I can help you check eligibility and explain the next steps.</p>
          </div>
          <p className="landing-preview-caption">Tap start and speak naturally</p>
        </div>
      </div>
      <div className="mx-auto grid w-full max-w-4xl gap-3 pt-9 pb-10 sm:grid-cols-3 sm:pb-4">
        {features.map(({ icon: Icon, title, copy }, index) => (
          <button
            key={title}
            type="button"
            onClick={onStartCall}
            className="feature-card focus-visible:ring-ring min-h-20 w-full text-left focus-visible:ring-3"
            style={{ animationDelay: `${index * 110}ms` }}
          >
            <div className="feature-icon">
              <Icon size={19} />
            </div>
            <div>
              <p className="text-sm font-bold">{title}</p>
              <p className="text-muted-foreground mt-1 text-xs">{copy}</p>
            </div>
            <ArrowUpRight size={16} className="feature-arrow" />
          </button>
        ))}
      </div>
      <p className="gov-guidance">
        DhanSathi provides general guidance. For final decisions, always use verified official
        portals and your bank's official channels.
      </p>
    </section>
  </div>
);
