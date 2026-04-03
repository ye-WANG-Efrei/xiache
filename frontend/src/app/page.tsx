"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { Loader2, AlertCircle, Cpu } from "lucide-react";
import { SkillCard } from "@/components/SkillCard";
import { SearchBar } from "@/components/SearchBar";
import { defaultClient, type RecordMetadataItem } from "@/lib/api";

// BM25-lite client-side ranking
function scoreRecord(record: RecordMetadataItem, query: string): number {
  if (!query) return 1;
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  const haystack = [record.name, record.description, ...record.tags, record.record_id]
    .join(" ")
    .toLowerCase();
  return tokens.reduce((acc, token) => {
    const count = (haystack.match(new RegExp(token, "g")) ?? []).length;
    return acc + Math.log1p(count);
  }, 0);
}

const VISIBILITY_OPTIONS = [
  { value: "all",        label: "ALL VISIBILITY" },
  { value: "public",     label: "PUBLIC" },
  { value: "group_only", label: "GROUP ONLY" },
];

const LEVEL_OPTIONS = [
  { value: "all",        label: "ALL LEVELS" },
  { value: "workflow",   label: "WORKFLOW" },
  { value: "tool_guide", label: "TOOL GUIDE" },
  { value: "reference",  label: "REFERENCE" },
];

export default function HomePage() {
  const [skills, setSkills] = useState<RecordMetadataItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [levelFilter, setLevelFilter] = useState("all");
  const [cursor, setCursor] = useState<string | undefined>();
  const [hasMore, setHasMore] = useState(false);
  const [total, setTotal] = useState(0);

  const fetchPage = useCallback(
    async (append = false, nextCursor?: string) => {
      try {
        if (!append) setLoading(true);
        const page = await defaultClient.listRecordsMetadata({
          limit: 48,
          cursor: nextCursor,
          visibility: visibilityFilter !== "all" ? visibilityFilter : undefined,
        });
        setSkills((prev) => (append ? [...prev, ...page.items] : page.items));
        setHasMore(page.has_more);
        setCursor(page.next_cursor ?? undefined);
        setTotal(page.total);
        setError(null);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load skills");
      } finally {
        setLoading(false);
      }
    },
    [visibilityFilter]
  );

  useEffect(() => { fetchPage(false, undefined); }, [fetchPage]);

  const filtered = useMemo(() => {
    let items = skills;
    if (levelFilter !== "all") items = items.filter((s) => s.level === levelFilter);
    if (!query.trim()) return items;
    return items
      .map((s) => ({ s, score: scoreRecord(s, query) }))
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ s }) => s);
  }, [skills, query, levelFilter]);

  return (
    <div>
      {/* ── Hero ── */}
      <div className="relative mb-10 overflow-hidden">
        {/* Grid background */}
        <div className="absolute inset-0 bg-grid opacity-60 pointer-events-none" />
        {/* Scan sweep */}
        <div className="absolute inset-0 scan-sweep pointer-events-none" />

        <div className="relative z-10 py-10 px-2">
          {/* Label */}
          <div className="flex items-center gap-2 mb-3 justify-center">
            <span className="h-px w-8 bg-cyber-cyan opacity-50" />
            <span className="label-cyber text-cyber-cyan tracking-[0.3em]">
              AGENT-NATIVE PLATFORM
            </span>
            <span className="h-px w-8 bg-cyber-cyan opacity-50" />
          </div>

          {/* Main title */}
          <h1
            className="text-center font-display font-bold leading-none"
            style={{ fontSize: "clamp(2.4rem, 6vw, 5rem)", letterSpacing: "0.06em" }}
          >
            <span className="text-cyber-yellow" style={{ textShadow: "0 0 30px rgba(255,230,0,0.4), 0 0 60px rgba(255,230,0,0.15)" }}>
              SKILL
            </span>
            {" "}
            <span className="text-cyber-text">REGISTRY</span>
          </h1>

          {/* Subtitle */}
          <p className="mt-3 text-center font-mono text-sm text-cyber-muted max-w-lg mx-auto">
            &gt;_ Discover, version &amp; share AI agent skills.
            {" "}
            <span className="text-cyber-cyan">Control agents like GitHub controls code.</span>
          </p>

          {/* Stats strip */}
          {!loading && !error && (
            <div className="mt-6 flex items-center justify-center gap-6">
              <div className="flex items-center gap-2">
                <span className="status-dot status-dot-running" />
                <span className="font-mono text-xs text-cyber-muted">
                  <span className="text-cyber-cyan font-semibold">{total}</span> SKILLS INDEXED
                </span>
              </div>
              {filtered.length !== total && (
                <>
                  <span className="h-3 w-px bg-cyber-border" />
                  <div className="flex items-center gap-2">
                    <span className="status-dot status-dot-success" />
                    <span className="font-mono text-xs text-cyber-muted">
                      <span className="text-cyber-green font-semibold">{filtered.length}</span> MATCHING
                    </span>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Bottom border glow */}
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyber-yellow to-transparent opacity-40" />
      </div>

      {/* ── Controls ── */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchBar value={query} onChange={setQuery} className="flex-1" />

        <div className="flex gap-2">
          {/* Visibility filter */}
          <div className="relative">
            <select
              value={visibilityFilter}
              onChange={(e) => setVisibilityFilter(e.target.value)}
              className="
                appearance-none bg-cyber-card border border-cyber-border text-cyber-muted
                px-3 py-2 pr-7 text-xs font-mono tracking-wider outline-none
                hover:border-cyber-dim hover:text-cyber-text transition-colors cursor-pointer
                focus:border-cyber-cyan focus:text-cyber-cyan
              "
              style={{ clipPath: "polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px)" }}
            >
              {VISIBILITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-cyber-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          {/* Level filter */}
          <div className="relative">
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="
                appearance-none bg-cyber-card border border-cyber-border text-cyber-muted
                px-3 py-2 pr-7 text-xs font-mono tracking-wider outline-none
                hover:border-cyber-dim hover:text-cyber-text transition-colors cursor-pointer
                focus:border-cyber-cyan focus:text-cyber-cyan
              "
              style={{ clipPath: "polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px)" }}
            >
              {LEVEL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3 w-3 text-cyber-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="flex flex-col items-center justify-center gap-4 py-24">
          <Loader2 className="h-6 w-6 animate-spin text-cyber-cyan" />
          <span className="font-mono text-xs text-cyber-muted tracking-widest animate-cyber-pulse">
            LOADING SKILL DATABASE...
          </span>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div
          className="flex flex-col items-center gap-4 border border-cyber-pink bg-cyber-pink-dim p-10 text-center"
          style={{ clipPath: "polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px)" }}
        >
          <AlertCircle className="h-8 w-8 text-cyber-pink" style={{ filter: "drop-shadow(0 0 6px rgba(255,0,60,0.6))" }} />
          <p className="font-mono text-sm font-medium text-cyber-pink">{error}</p>
          <button
            onClick={() => fetchPage(false)}
            className="btn-cyber text-xs"
          >
            RETRY CONNECTION
          </button>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && !error && filtered.length === 0 && (
        <div
          className="flex flex-col items-center gap-4 border border-dashed border-cyber-border p-16 text-center"
          style={{ clipPath: "polygon(12px 0,100% 0,100% calc(100% - 12px),calc(100% - 12px) 100%,0 100%,0 12px)" }}
        >
          <Cpu className="h-10 w-10 text-cyber-faint" />
          <p className="font-mono text-sm text-cyber-muted">
            {query || levelFilter !== "all"
              ? "> NO SKILLS MATCH QUERY"
              : "> NO SKILLS REGISTERED"}
          </p>
        </div>
      )}

      {/* ── Grid ── */}
      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((skill) => (
            <SkillCard key={skill.record_id} skill={skill} />
          ))}
        </div>
      )}

      {/* ── Load more ── */}
      {hasMore && !query && levelFilter === "all" && (
        <div className="mt-8 flex justify-center">
          <button
            onClick={() => fetchPage(true, cursor)}
            className="btn-cyber-ghost text-xs tracking-widest"
          >
            LOAD MORE SKILLS
          </button>
        </div>
      )}
    </div>
  );
}
