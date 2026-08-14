'use client';

import { ArrowRight, CheckCircle2 } from 'lucide-react';

export interface SchemeResult {
  scheme: string;
  amount: string;
  detail: string;
  eligible: boolean;
}

export function SchemeResultCard({ result }: { result: SchemeResult }) {
  return (
    <article className="scheme-result-card" aria-label={`${result.scheme} eligibility result`}>
      <div className="flex items-start gap-2">
        <CheckCircle2 className="text-success mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <div>
          <p className="text-sm font-extrabold text-[#FDE7B0]">{result.scheme} योजना</p>
          <p className="mt-0.5 text-sm font-bold text-white">{result.amount}</p>
          <p className="mt-1 text-xs leading-5 text-slate-300">{result.detail}</p>
        </div>
      </div>
      <button
        type="button"
        className="scheme-result-action"
        aria-label={`${result.scheme} के अगले कदम देखें · View next steps`}
      >
        अगला कदम <span className="text-slate-400">· Next step</span>
        <ArrowRight className="size-3.5" aria-hidden="true" />
      </button>
    </article>
  );
}
