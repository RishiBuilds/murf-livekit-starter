import { ReactNode, useCallback, useEffect, useState } from 'react';
import { toast as sonnerToast } from 'sonner';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { MicPermissionError } from '@/components/app/mic-permission-error';

interface ToastProps {
  title: ReactNode;
  description: ReactNode;
}

function toastAlert(toast: ToastProps) {
  const { title, description } = toast;

  return sonnerToast.custom(
    (id) => (
      <Alert onClick={() => sonnerToast.dismiss(id)} className="bg-accent w-full md:w-[364px]">
        <WarningIcon weight="bold" />
        <AlertTitle>{title}</AlertTitle>
        {description && <AlertDescription>{description}</AlertDescription>}
      </Alert>
    ),
    { duration: 10_000 }
  );
}

/**
 * Checks whether a mic-permission error has occurred.
 * Detects NotAllowedError (permission denied) and NotFoundError (no mic device).
 */
function isMicPermissionError(error: unknown): boolean {
  if (error instanceof DOMException) {
    return error.name === 'NotAllowedError' || error.name === 'NotFoundError';
  }
  // LiveKit sometimes wraps mic errors in failure reasons
  if (typeof error === 'string') {
    const lower = error.toLowerCase();
    return (
      lower.includes('permission') ||
      lower.includes('not allowed') ||
      lower.includes('microphone') ||
      lower.includes('notallowederror') ||
      lower.includes('notfounderror')
    );
  }
  return false;
}

export function useAgentErrors() {
  const agent = useAgent();
  const { isConnected, end } = useSessionContext();
  const [showMicError, setShowMicError] = useState(false);

  // Listen for mic permission errors during session
  useEffect(() => {
    const handleDeviceError = (event: Event) => {
      if (event instanceof ErrorEvent && isMicPermissionError(event.error)) {
        setShowMicError(true);
      }
    };

    window.addEventListener('error', handleDeviceError);
    return () => window.removeEventListener('error', handleDeviceError);
  }, []);

  useEffect(() => {
    const handleMicControlError = (event: Event) => {
      const error = (event as CustomEvent<unknown>).detail;
      if (isMicPermissionError(error)) setShowMicError(true);
    };

    window.addEventListener('dhan-mic-error', handleMicControlError);
    return () => window.removeEventListener('dhan-mic-error', handleMicControlError);
  }, []);

  // Check failure reasons for mic-related errors
  useEffect(() => {
    if (isConnected && agent.state === 'failed') {
      const reasons = agent.failureReasons;

      // Check if any failure reason is mic-related
      const hasMicError = reasons.some((reason) => isMicPermissionError(reason));

      if (hasMicError) {
        setShowMicError(true);
        end();
        return;
      }

      // Non-mic errors: show toast
      toastAlert({
        title: 'सत्र समाप्त हुआ · Session ended',
        description: (
          <>
            {reasons.length > 1 && (
              <ul className="list-inside list-disc">
                {reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {reasons.length === 1 && <p className="w-full">{reasons[0]}</p>}
            <p className="w-full">
              <a
                target="_blank"
                rel="noopener noreferrer"
                href="https://docs.livekit.io/agents/start/voice-ai/"
                className="whitespace-nowrap underline"
              >
                See quickstart guide
              </a>
              .
            </p>
          </>
        ),
      });

      end();
    }
  }, [agent, isConnected, end]);

  const handleMicRetry = useCallback(() => {
    setShowMicError(false);
    // Reload to reset the session after mic permission is granted
    window.location.reload();
  }, []);

  const handleMicDismiss = useCallback(() => {
    setShowMicError(false);
  }, []);

  return {
    showMicError,
    MicErrorOverlay: showMicError ? (
      <MicPermissionError onRetry={handleMicRetry} onDismiss={handleMicDismiss} />
    ) : null,
  };
}
