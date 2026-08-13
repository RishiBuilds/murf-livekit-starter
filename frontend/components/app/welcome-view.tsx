import {
  ArrowUpRight,
  BadgeIndianRupee,
  BarChart3,
  Headphones,
  Landmark,
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
      <div className="flex items-center justify-between">
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
        <div className="flex items-center gap-2">
          <a
            href="/analytics"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-3.5 py-1.5 text-xs font-bold text-emerald-300 shadow-sm transition-all hover:border-emerald-500/40 hover:bg-emerald-500/20"
          >
            <BarChart3 size={14} className="text-emerald-400" />
            <span>Call Analytics</span>
          </a>
          <a
            href="/escalations"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3.5 py-1.5 text-xs font-bold text-indigo-300 shadow-sm transition-all hover:border-indigo-500/40 hover:bg-indigo-500/20"
          >
            <Headphones size={14} className="text-indigo-400" />
            <span>Open Escalations</span>
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
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center text-center">
        <div className="voice-orb mb-7 sm:mb-9">
          <div className="voice-orb-ring voice-orb-ring-one" />
          <div className="voice-orb-ring voice-orb-ring-two" />
          <div className="voice-orb-core">
            <Mic size={34} strokeWidth={2.2} />
          </div>
          <span className="voice-orb-pulse" />
        </div>
        <div className="eyebrow">
          <Sparkles size={14} />
          Financial guidance for every Indian
        </div>
        <h1 className="mt-5 max-w-2xl text-4xl font-black tracking-[-0.055em] text-balance sm:text-5xl md:text-6xl">
          Benefits, banking and safety.{' '}
          <span className="text-gradient">Made easy to understand.</span>
        </h1>
        <p className="text-muted-foreground mt-5 max-w-xl text-sm leading-6 sm:text-base sm:leading-7">
          सरकारी योजनाएँ, banking help और fraud safety. बस बोलिए। Get clear guidance in simple Hindi
          or English.
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
        <div className="border-success/25 bg-success/8 mt-4 max-w-sm rounded-xl border px-3 py-2 text-left">
          <p className="text-foreground text-xs font-bold">
            AI assistant · DhanSathi kabhi OTP, PIN, ya paise nahi maangti.
          </p>
          <p className="text-muted-foreground mt-0.5 text-[11px]">
            No forms. No jargon. Just start speaking.
          </p>
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
