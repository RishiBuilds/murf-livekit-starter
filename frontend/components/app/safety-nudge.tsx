'use client';

import { useMemo } from 'react';
import { ShieldAlert } from 'lucide-react';
import { useSessionContext, useSessionMessages } from '@livekit/components-react';

const RISK_PATTERN =
  /(?:otp|\bpin\b|cvv|password|aadhaar|aadhar).{0,80}(?:share|give|tell|send|ask)|(?:share|give|tell|send|ask).{0,80}(?:otp|\bpin\b|cvv|password|aadhaar|aadhar)|anydesk|teamviewer|remote access|screen share|money deducted|unauthori[sz]ed transaction|paise (?:kat|chale gaye)/i;

/** A visible safety backstop while the agent gives the spoken fraud warning. */
export function SafetyNudge() {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const isRisky = useMemo(
    () => messages.some(({ from, message }) => from?.isLocal && RISK_PATTERN.test(message)),
    [messages]
  );

  if (!isRisky) return null;

  return (
    <aside
      role="alert"
      className="border-destructive/35 bg-background/95 absolute inset-x-4 top-24 z-30 mx-auto max-w-md rounded-2xl border p-4 shadow-xl backdrop-blur md:top-28"
    >
      <div className="flex gap-3">
        <ShieldAlert className="text-destructive mt-0.5 shrink-0" aria-hidden="true" />
        <div>
          <p className="text-sm font-extrabold">Rukiye — OTP ya PIN kabhi share na karein.</p>
          <p className="text-muted-foreground mt-1 text-xs leading-5">
            Stop. Do not share a code, password, or Aadhaar number. If money is at risk, call 1930
            now.
          </p>
        </div>
      </div>
    </aside>
  );
}
