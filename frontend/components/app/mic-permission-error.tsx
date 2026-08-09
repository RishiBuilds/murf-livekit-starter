'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/shadcn/utils';

interface MicPermissionErrorProps {
  onRetry: () => void;
  onDismiss: () => void;
  className?: string;
}

/**
 * Detects the user's browser for showing relevant mic permission instructions.
 * Prioritizes mobile Chrome (Android) since the target audience is mobile-first.
 */
function detectBrowser(): 'android-chrome' | 'ios-safari' | 'desktop-chrome' | 'desktop-firefox' | 'other' {
  if (typeof navigator === 'undefined') return 'other';
  const ua = navigator.userAgent;

  // Android Chrome (most common for target audience)
  if (/Android/i.test(ua) && /Chrome/i.test(ua) && !/Edge/i.test(ua)) {
    return 'android-chrome';
  }
  // iOS Safari
  if (/iPhone|iPad|iPod/i.test(ua) && /Safari/i.test(ua)) {
    return 'ios-safari';
  }
  // Desktop Firefox
  if (/Firefox/i.test(ua) && !/Android/i.test(ua)) {
    return 'desktop-firefox';
  }
  // Desktop Chrome
  if (/Chrome/i.test(ua) && !/Edge/i.test(ua) && !/Android/i.test(ua)) {
    return 'desktop-chrome';
  }

  return 'other';
}

/**
 * Browser-specific mic permission instructions in Hindi and English.
 * Android Chrome is listed first since the target audience is overwhelmingly mobile-first.
 */
function BrowserInstructions({ browser }: { browser: ReturnType<typeof detectBrowser> }) {
  return (
    <div className="mt-6 space-y-5 text-left">
      {/* Android Chrome: primary instructions */}
      <div className={cn(
        'rounded-xl border p-4',
        browser === 'android-chrome'
          ? 'bg-primary/5 border-primary/20'
          : 'border-border/50'
      )}>
        <h3 className="text-foreground mb-2 text-sm font-bold">
          📱 Android Chrome {browser === 'android-chrome' && (
            <span className="bg-primary/15 text-primary ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
              आपका ब्राउज़र · Your browser
            </span>
          )}
        </h3>
        <ol className="text-foreground/70 space-y-1.5 text-xs leading-5 md:text-sm">
          <li>1. एड्रेस बार में 🔒 आइकन दबाएं</li>
          <li className="text-muted-foreground pl-4 text-[10px] italic">Tap the 🔒 icon in the address bar</li>
          <li>2. &quot;साइट सेटिंग&quot; चुनें</li>
          <li className="text-muted-foreground pl-4 text-[10px] italic">Select &quot;Site settings&quot;</li>
          <li>3. &quot;माइक्रोफ़ोन&quot; → &quot;अनुमति दें&quot;</li>
          <li className="text-muted-foreground pl-4 text-[10px] italic">Microphone → Allow</li>
          <li>4. पेज रीफ्रेश करें</li>
          <li className="text-muted-foreground pl-4 text-[10px] italic">Refresh the page</li>
        </ol>
      </div>

      {/* Desktop Chrome */}
      <div className={cn(
        'rounded-xl border p-4',
        browser === 'desktop-chrome'
          ? 'bg-primary/5 border-primary/20'
          : 'border-border/50'
      )}>
        <h3 className="text-foreground mb-2 text-sm font-bold">
          💻 Desktop Chrome {browser === 'desktop-chrome' && (
            <span className="bg-primary/15 text-primary ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
              Your browser
            </span>
          )}
        </h3>
        <ol className="text-foreground/70 space-y-1 text-xs leading-5 md:text-sm">
          <li>1. Click the 🔒 icon in the address bar</li>
          <li>2. Set Microphone to &quot;Allow&quot;</li>
          <li>3. Reload the page</li>
        </ol>
      </div>

      {/* iOS Safari */}
      <div className={cn(
        'rounded-xl border p-4',
        browser === 'ios-safari'
          ? 'bg-primary/5 border-primary/20'
          : 'border-border/50'
      )}>
        <h3 className="text-foreground mb-2 text-sm font-bold">
          🍎 Safari (iOS) {browser === 'ios-safari' && (
            <span className="bg-primary/15 text-primary ml-1 rounded-full px-2 py-0.5 text-[10px] font-semibold">
              आपका ब्राउज़र · Your browser
            </span>
          )}
        </h3>
        <p className="text-foreground/70 text-xs leading-5 md:text-sm">
          Settings → Safari → Microphone → Allow
        </p>
      </div>
    </div>
  );
}

/**
 * Full-screen overlay shown when microphone permission is denied.
 * Bilingual Hindi + English instructions, mobile-first (Android Chrome priority).
 */
export function MicPermissionError({ onRetry, onDismiss, className }: MicPermissionErrorProps) {
  const [retrying, setRetrying] = useState(false);
  const [retryFailed, setRetryFailed] = useState(false);
  const browser = detectBrowser();

  const handleRetry = async () => {
    setRetrying(true);
    setRetryFailed(false);

    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      // Permission granted. Reload to reconnect.
      onRetry();
    } catch {
      // Still blocked. Show manual instructions.
      setRetryFailed(true);
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className={cn(
      'bg-background/95 fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-md',
      className
    )}>
      <div className="mx-4 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl p-6 md:p-8">
        {/* Header */}
        <div className="mb-4 text-center">
          <div className="bg-destructive/10 mx-auto mb-4 flex size-16 items-center justify-center rounded-full">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-destructive"
            >
              <line x1="1" y1="1" x2="23" y2="23" />
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.13 1.49-.35 2.17" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </div>

          <h2 className="text-foreground text-lg font-bold md:text-xl">
            🎙️ माइक्रोफ़ोन की अनुमति ज़रूरी है
          </h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Microphone access is required
          </p>
          <p className="text-muted-foreground mt-2 text-xs leading-5">
            DhanSathi को आपकी बात सुनने के लिए माइक्रोफ़ोन की ज़रूरत है।
            <br />
            DhanSathi needs your microphone to hear you.
          </p>
        </div>

        {/* Retry failed notice */}
        {retryFailed && (
          <div className="bg-destructive/10 border-destructive/20 mb-4 rounded-lg border p-3 text-center">
            <p className="text-destructive text-xs font-medium">
              अनुमति अभी भी अवरुद्ध है। नीचे दिए गए चरणों का पालन करें।
              <br />
              Permission is still blocked. Follow the steps below.
            </p>
          </div>
        )}

        {/* Browser-specific instructions */}
        <BrowserInstructions browser={browser} />

        {/* Action buttons */}
        <div className="mt-6 flex flex-col gap-3">
          <Button
            size="lg"
            onClick={handleRetry}
            disabled={retrying}
            className="w-full rounded-full font-sans text-sm font-bold"
          >
            {retrying ? (
              <span className="flex items-center gap-2">
                <span className="border-primary-foreground/30 border-t-primary-foreground size-4 animate-spin rounded-full border-2" />
                कोशिश कर रहे हैं…
              </span>
            ) : (
              'फिर से कोशिश करें · Try Again'
            )}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="text-muted-foreground text-xs"
          >
            बिना माइक के जारी रखें · Continue without mic
          </Button>
        </div>
      </div>
    </div>
  );
}
