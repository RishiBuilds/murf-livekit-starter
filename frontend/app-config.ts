export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;
  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;
  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;
  agentName?: string;
  sandboxId?: string;
  supportedLanguages?: string[];
  disclaimerText?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'DhanSathi',
  pageTitle: 'DhanSathi: PM-KISAN, PMJDY, UPI Safety & Banking Help',
  pageDescription: 'Talk to DhanSathi for government schemes, banking guidance, KYC help, and fraud safety.',
  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,
  logo: '/murf-logo.svg',
  accent: '#f5a623',
  logoDark: '/murf-logo-dark.svg',
  accentDark: '#ffc857',
  startButtonText: 'बातचीत शुरू करें · Start conversation',
  audioVisualizerType: 'aura',
  audioVisualizerColor: '#f5a623',
  audioVisualizerColorDark: '#ffc857',
  agentName: process.env.AGENT_NAME ?? undefined,
  sandboxId: undefined,
  supportedLanguages: ['hi', 'en'],
  disclaimerText: 'केवल मार्गदर्शन हेतु। बैंक/RBI की आधिकारिक सलाह का विकल्प नहीं है। · For guidance only. Not a substitute for official bank/RBI advice.',
};
