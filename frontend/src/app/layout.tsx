import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "xiache — Agent Skill Registry",
  description:
    "Agent-native open source platform. Browse, search, and version AI agent skills.",
  openGraph: {
    title: "xiache",
    description:
      "Agent-native open source skill registry. Discover, evolve, and share AI agent skills.",
    type: "website",
  },
};

const NAV_ITEMS = [
  { label: "Skills",     href: "/" },
  { label: "Tasks",      href: "/tasks" },
  { label: "Executions", href: "/executions" },
  { label: "Reviews",    href: "/reviews" },
] as const;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Manrope:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full bg-cyber-black text-cyber-text antialiased">

        {/* ── Navigation ── */}
        <nav className="sticky top-0 z-30 border-b border-cyber-border bg-cyber-black/95 backdrop-blur-sm">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center px-6">

            {/* Logo */}
            <a href="/" className="mr-8 flex items-center gap-2.5 group flex-shrink-0">
              <svg
                className="h-5 w-5 text-cyber-cyan group-hover:text-cyber-yellow transition-colors duration-200"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5" />
                <circle cx="12" cy="12" r="2.2" fill="currentColor" strokeWidth="0" />
              </svg>
              <span className="font-display font-bold text-[1.3rem] tracking-tight text-cyber-text group-hover:text-cyber-yellow transition-colors duration-200"
                style={{ letterSpacing: "-0.03em" }}>
                xiache
              </span>
            </a>

            <div className="h-5 w-px bg-cyber-border mr-6 flex-shrink-0" />

            {/* Nav links */}
            <div className="flex items-center overflow-x-auto flex-1">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="
                    relative flex items-center px-3 py-4 text-[0.875rem]
                    text-cyber-muted hover:text-cyber-text transition-colors duration-150
                    whitespace-nowrap group
                  "
                >
                  {item.label}
                  <span className="
                    absolute bottom-0 left-3 right-3 h-px bg-cyber-text
                    scale-x-0 group-hover:scale-x-100
                    transition-transform duration-200 origin-left
                  " />
                </a>
              ))}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-5 text-[0.875rem] text-cyber-muted flex-shrink-0">
              <a
                href="https://github.com/ye-WANG-Efrei/xiache"
                className="hover:text-cyber-text transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
              <span className="h-3.5 w-px bg-cyber-border" />
              <a href="/docs" className="hover:text-cyber-text transition-colors">
                Docs
              </a>
              <span className="h-3.5 w-px bg-cyber-border" />
              <div className="flex items-center justify-center w-7 h-7 rounded-full bg-cyber-dark border border-cyber-border text-cyber-muted text-xs font-medium hover:border-cyber-dim hover:text-cyber-text transition-all cursor-pointer select-none">
                YW
              </div>
            </div>
          </div>
        </nav>

        {/* ── Page content ── */}
        <main className="mx-auto max-w-[1400px] px-6 py-10">
          {children}
        </main>

        {/* ── Footer ── */}
        <footer className="mt-20 border-t border-cyber-border">
          <div className="mx-auto max-w-[1400px] px-6 py-8">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2.5">
                <svg className="h-4 w-4 text-cyber-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5" />
                </svg>
                <span className="font-display text-base text-cyber-text">xiache</span>
                <span className="text-cyber-faint text-sm">— Agent-native open source platform</span>
              </div>
              <div className="flex items-center gap-4 text-sm text-cyber-faint">
                <span>Apache 2.0</span>
                <span className="h-3 w-px bg-cyber-border" />
                <span>Built for the agent ecosystem</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
