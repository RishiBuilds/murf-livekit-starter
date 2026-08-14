import { Inter, Noto_Sans_Devanagari } from 'next/font/google';
import localFont from 'next/font/local';
import { headers } from 'next/headers';
import { ThemeProvider } from '@/components/app/theme-provider';
import { ThemeToggle } from '@/components/app/theme-toggle';
import { cn } from '@/lib/shadcn/utils';
import { getAppConfig, getStyles } from '@/lib/utils';
import '@/styles/globals.css';

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
});

const notoDevanagari = Noto_Sans_Devanagari({
  variable: '--font-noto-devanagari',
  subsets: ['devanagari'],
});

const commitMono = localFont({
  display: 'swap',
  variable: '--font-commit-mono',
  src: [
    {
      path: '../fonts/CommitMono-400-Regular.otf',
      weight: '400',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-700-Regular.otf',
      weight: '700',
      style: 'normal',
    },
    {
      path: '../fonts/CommitMono-400-Italic.otf',
      weight: '400',
      style: 'italic',
    },
    {
      path: '../fonts/CommitMono-700-Italic.otf',
      weight: '700',
      style: 'italic',
    },
  ],
});

interface RootLayoutProps {
  children: React.ReactNode;
}

export default async function RootLayout({ children }: RootLayoutProps) {
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);
  const styles = getStyles(appConfig);
  const { pageTitle, pageDescription, companyName, logo, logoDark, disclaimerText } = appConfig;

  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        inter.variable,
        notoDevanagari.variable,
        commitMono.variable,
        'scroll-smooth font-sans antialiased'
      )}
    >
      <head>
        {styles && <style>{styles}</style>}
        <title>{pageTitle}</title>
        <meta name="description" content={pageDescription} />
      </head>
      <body className="overflow-x-hidden">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <header className="hidden">
            <a href="/" className="scale-100 transition-transform duration-300 hover:scale-110">
              <img src={logo} alt={`${companyName} Logo`} className="block size-6 dark:hidden" />
              <img
                src={logoDark ?? logo}
                alt={`${companyName} Logo`}
                className="hidden size-6 dark:block"
              />
            </a>
            <span className="text-foreground font-sans text-xs font-bold tracking-wider uppercase">
              DhanSathi: आपका वित्तीय साथी
            </span>
          </header>

          {children}

          {disclaimerText && (
            <footer className="fixed bottom-0 left-0 z-40 w-full">
              <div className="bg-background/80 border-border/30 mx-auto border-t px-4 py-2 text-center backdrop-blur-sm">
                <p className="text-muted-foreground text-[10px] leading-4 md:text-xs">
                  {disclaimerText}
                </p>
              </div>
            </footer>
          )}

          <div className="group fixed bottom-8 left-1/2 z-50 mb-2 -translate-x-1/2">
            <ThemeToggle className="translate-y-20 transition-transform delay-150 duration-300 group-hover:translate-y-0" />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
