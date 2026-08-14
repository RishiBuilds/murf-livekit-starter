import type { ReceivedMessage } from '@livekit/components-react';

export interface CallRecap {
  topic: string;
  outcome: string;
  nextStep: string;
  transcriptExcerpt: Array<{ fromUser: boolean; text: string }>;
  eligibleSchemes: string[];
  escalationRef?: string;
}

const SENSITIVE_PATTERN = /\b(?:\d{4}[\s-]?){3}\d{0,4}\b|\b[A-Z]{5}\d{4}[A-Z]\b|\b\d{9,18}\b/g;

function hasText(messages: ReceivedMessage[], pattern: RegExp) {
  return messages.some(({ message }) => pattern.test(message));
}

export function createCallRecap(messages: ReceivedMessage[]): CallRecap {
  const transcriptExcerpt = messages.slice(-4).map(({ from, message }) => ({
    fromUser: from?.isLocal === true,
    text: message.replace(SENSITIVE_PATTERN, '[private]'),
  }));
  const safeTranscript = messages
    .map(({ message }) => message.replace(SENSITIVE_PATTERN, '[private]'))
    .join(' ')
    .toLowerCase();

  const eligibleSchemes = [
    /pm[ -]?kisan/.test(safeTranscript) && /eligible|पात्र|qualify|योग्य/.test(safeTranscript)
      ? 'PM-KISAN eligible'
      : '',
    /mudra/.test(safeTranscript) && /eligible|पात्र|qualify|योग्य/.test(safeTranscript)
      ? 'MUDRA guidance'
      : '',
  ].filter(Boolean);
  const escalationRef = messages
    .map(
      ({ message }) =>
        message.match(/(?:reference\s*(?:id|number)?|ref)\s*[:#-]?\s*(#[A-Z]{2,8}-\d{3,})/i)?.[1]
    )
    .find(Boolean);
  const shared = { transcriptExcerpt, eligibleSchemes, escalationRef };

  if (/otp|pin|cvv|fraud|scam|1930|unauthori[sz]ed|anydesk|teamviewer/.test(safeTranscript)) {
    return {
      topic: 'Fraud safety / धोखाधड़ी से सुरक्षा',
      outcome: 'DhanSathi shared immediate fraud-safety guidance.',
      nextStep: 'Do not share codes or install remote-access apps. If money is at risk, call 1930.',
      ...shared,
    };
  }

  if (hasText(messages, /pm[ -]?kisan|mudra|atal pension|apy|pmay|awas|jan dhan|pmjdy/i)) {
    return {
      topic: 'Scheme guidance / योजना मार्गदर्शन',
      outcome: 'Your result is a guidance check, not final approval.',
      nextStep: 'Take the required documents to a CSC, bank branch, or official portal to verify.',
      ...shared,
    };
  }

  return {
    topic: 'Financial guidance / वित्तीय सहायता',
    outcome: 'DhanSathi shared general financial guidance during this call.',
    nextStep: 'Use only verified bank, CSC, and government channels for your next step.',
    ...shared,
  };
}
