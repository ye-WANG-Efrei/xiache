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
  { label: "DASHBOARD",   href: "/dashboard" },
  { label: "SKILLS",      href: "/" },
  { label: "TASKS",       href: "/tasks" },
  { label: "EXECUTIONS",  href: "/executions" },
  { label: "REVIEWS",     href: "/reviews" },
  { label: "REGISTRY",    href: "/registry" },
  { label: "DEVICES",     href: "/devices" },
  { label: "PROJECTS",    href: "/projects" },
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
          href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&family=Exo+2:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="h-full bg-cyber-black text-cyber-text antialiased">

        {/* ── Top bar: logo + version strip ── */}
        <div className="border-b border-cyber-border bg-cyber-black">
          <div className="mx-auto flex h-8 max-w-[1400px] items-center justify-between px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <span className="font-mono text-[10px] text-cyber-faint tracking-widest">
                XIACHE_OS v0.1.0
              </span>
              <span className="h-3 w-px bg-cyber-border" />
              <span className="font-mono text-[10px] text-cyber-cyan animate-cyber-pulse">
                ● SYSTEM ONLINE
              </span>
            </div>
            <div className="flex items-center gap-4 font-mono text-[10px] text-cyber-faint tracking-wider">
              <a
                href="https://github.com/ye-WANG-Efrei/xiache"
                className="hover:text-cyber-cyan transition-colors"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
              <span className="h-3 w-px bg-cyber-border" />
              <a href="/docs" className="hover:text-cyber-cyan transition-colors">
                API Docs
              </a>
            </div>
          </div>
        </div>

        {/* ── Main nav ── */}
        <nav className="sticky top-0 z-30 border-b border-cyber-border bg-cyber-black/95 backdrop-blur-sm">
          {/* Yellow accent line */}
          <div className="h-px w-full bg-gradient-to-r from-transparent via-cyber-yellow to-transparent opacity-60" />

          <div className="mx-auto flex h-12 max-w-[1400px] items-center gap-0 px-4 sm:px-6">
            {/* Logo */}
            <a
              href="/"
              className="mr-6 flex items-center gap-2 group flex-shrink-0"
            >
              {/* Hexagon icon */}
              <svg
                className="h-7 w-7 text-cyber-yellow drop-shadow-[0_0_6px_rgba(255,230,0,0.5)] group-hover:drop-shadow-[0_0_12px_rgba(255,230,0,0.8)] transition-all"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5" />
                <line x1="12" y1="22" x2="12" y2="16.5" strokeWidth="1" />
                <polyline points="22 7.5 12 16.5 2 7.5" strokeWidth="1" />
                {/* Inner detail */}
                <circle cx="12" cy="12" r="2" fill="currentColor" strokeWidth="0" />
              </svg>
              <span
                className="font-display font-bold text-xl tracking-widest text-cyber-yellow"
                style={{ textShadow: "0 0 12px rgba(255,230,0,0.4)" }}
              >
                XIACHE
              </span>
            </a>

            {/* Separator */}
            <div className="h-6 w-px bg-cyber-border mr-4 flex-shrink-0" />

            {/* Nav items */}
            <div className="flex items-center gap-0 overflow-x-auto scrollbar-none flex-1">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="
                    relative flex items-center px-3 py-3 text-xs font-display font-semibold tracking-widest
                    text-cyber-muted hover:text-cyber-yellow transition-colors duration-150
                    whitespace-nowrap group
                  "
                >
                  {item.label}
                  {/* Hover underline glow */}
                  <span className="
                    absolute bottom-0 left-0 right-0 h-px bg-cyber-yellow scale-x-0
                    group-hover:scale-x-100 transition-transform duration-150 origin-left
                    shadow-[0_0_4px_rgba(255,230,0,0.8)]
                  " />
                </a>
              ))}
            </div>

            {/* Right: notifications + user */}
            <div className="flex items-center gap-2 flex-shrink-0 ml-2">
              {/* Notifications */}
              <a
                href="/notifications"
                className="relative flex items-center justify-center w-8 h-8 border border-cyber-border hover:border-cyber-cyan hover:text-cyber-cyan text-cyber-muted transition-all"
                style={{ clipPath: "polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)" }}
              >
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                  <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                </svg>
                {/* Badge */}
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-cyber-pink rounded-full animate-cyber-pulse" />
              </a>

              {/* User avatar placeholder */}
              <div
                className="flex items-center justify-center w-8 h-8 bg-cyber-card border border-cyber-border text-cyber-muted font-mono text-xs hover:border-cyber-yellow hover:text-cyber-yellow transition-all cursor-pointer"
                style={{ clipPath: "polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)" }}
              >
                YW
              </div>
            </div>
          </div>

          {/* Bottom cyan accent */}
          <div className="h-px w-full bg-gradient-to-r from-transparent via-cyber-cyan to-transparent opacity-20" />
        </nav>

        {/* ── Page content ── */}
        <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6">
          {children}
        </main>

        {/* ── Footer ── */}
        <footer className="mt-16 border-t border-cyber-border bg-cyber-black">
          <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2">
                <svg className="h-4 w-4 text-cyber-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="12 2 22 7.5 22 16.5 12 22 2 16.5 2 7.5" />
                </svg>
                <span className="font-display font-semibold text-sm tracking-widest text-cyber-yellow">XIACHE</span>
                <span className="font-mono text-xs text-cyber-faint">— Agent-native open source platform</span>
              </div>
              <div className="flex items-center gap-4 font-mono text-xs text-cyber-faint">
                <span>Apache 2.0</span>
                <span className="h-3 w-px bg-cyber-border" />
                <span className="text-cyber-cyan">Built for the agent ecosystem</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
