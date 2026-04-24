"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { Loader2, AlertCircle, Inbox } from "lucide-react";
import { SkillCard } from "@/components/SkillCard";
import { SearchBar } from "@/components/SearchBar";
import { defaultClient, type RecordMetadataItem, type CategoryItem } from "@/lib/api";

// BM25-lite client-side ranking
function scoreRecord(record: RecordMetadataItem, query: string): number {
  if (!query) return 1;
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  const haystack = [record.name, record.description, ...(record.tags ?? [])]
    .join(" ")
    .toLowerCase();
  return tokens.reduce((acc, token) => {
    const count = (haystack.match(new RegExp(token, "g")) ?? []).length;
    return acc + Math.log1p(count);
  }, 0);
}

const VISIBILITY_OPTIONS = [
  { value: "all",        label: "All visibility" },
  { value: "public",     label: "Public" },
  { value: "group_only", label: "Group only" },
];

const LEVEL_OPTIONS = [
  { value: "all",        label: "All types" },
  { value: "workflow",   label: "Workflow" },
  { value: "tool_guide", label: "Tool guide" },
  { value: "reference",  label: "Reference" },
];

export default function HomePage() {
  const [skills, setSkills] = useState<RecordMetadataItem[]>([]);
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [levelFilter, setLevelFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
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

  useEffect(() => {
    defaultClient.listCategories()
      .then((res) => setCategories(res.items))
      .catch(() => { /* categories are optional UI sugar */ });
  }, []);

  const filtered = useMemo(() => {
    let items = skills;
    if (levelFilter !== "all") items = items.filter((s) => s.level === levelFilter);
    if (categoryFilter !== "all") items = items.filter((s) => s.category === categoryFilter);
    if (!query.trim()) return items;
    return items
      .map((s) => ({ s, score: scoreRecord(s, query) }))
      .filter(({ score }) => score > 0)
      .sort((a, b) => b.score - a.score)
      .map(({ s }) => s);
  }, [skills, query, levelFilter, categoryFilter]);

  const isFiltered = categoryFilter !== "all" || levelFilter !== "all" || query.trim().length > 0;

  return (
    <div>
      {/* ── Hero ── */}
      <div className="mb-10 pt-4">
        {/* Top row: label + stats */}
        <div className="flex items-start justify-between gap-6 mb-5">
          <p className="text-xs font-medium tracking-widest text-cyber-cyan uppercase mt-1">
            Agent-native platform
          </p>
          {!loading && !error && (
            <div className="hidden sm:flex items-baseline gap-1.5 flex-shrink-0">
              <span className="font-display font-semibold text-cyber-text"
                style={{ fontSize: "clamp(2rem, 3vw, 2.75rem)", lineHeight: 1 }}>
                {total}
              </span>
              <span className="text-sm text-cyber-muted">skills</span>
              {isFiltered && (
                <>
                  <span className="text-cyber-faint mx-1">·</span>
                  <span className="font-display font-semibold text-cyber-yellow"
                    style={{ fontSize: "clamp(2rem, 3vw, 2.75rem)", lineHeight: 1 }}>
                    {filtered.length}
                  </span>
                  <span className="text-sm text-cyber-muted">shown</span>
                </>
              )}
            </div>
          )}
        </div>

        {/* Large heading */}
        <h1
          className="font-display font-bold text-cyber-text"
          style={{ fontSize: "clamp(3.5rem, 7vw, 6.5rem)", lineHeight: 1, letterSpacing: "-0.03em" }}
        >
          Skill Registry
        </h1>

        {/* Rule + description */}
        <div className="mt-5 pt-5 border-t border-cyber-border flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <p className="text-cyber-muted max-w-md leading-relaxed">
            Discover, version &amp; share AI agent skills.
            Control agents like GitHub controls code.
          </p>
          {!loading && !error && (
            <div className="sm:hidden flex items-center gap-3 text-sm text-cyber-muted">
              <span><span className="font-semibold text-cyber-text">{total}</span> skills</span>
              {isFiltered && (
                <><span className="text-cyber-faint">·</span>
                <span><span className="font-semibold text-cyber-text">{filtered.length}</span> shown</span></>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Category tabs ── */}
      {categories.length > 0 && (
        <div className="mb-6 border-b border-cyber-border">
          <div className="flex overflow-x-auto gap-0 scrollbar-none">
            <button
              onClick={() => setCategoryFilter("all")}
              className={[
                "relative flex-shrink-0 pb-3 pr-5 text-sm whitespace-nowrap transition-colors duration-150",
                categoryFilter === "all"
                  ? "text-cyber-text font-medium"
                  : "text-cyber-muted hover:text-cyber-text",
              ].join(" ")}
            >
              All
              {categoryFilter === "all" && (
                <span className="absolute bottom-0 left-0 right-3 h-[1.5px] bg-cyber-text" />
              )}
            </button>
            {categories.map((cat) => (
              <button
                key={cat.id}
                onClick={() => setCategoryFilter(cat.id === categoryFilter ? "all" : cat.id)}
                className={[
                  "relative flex-shrink-0 pb-3 px-4 text-sm whitespace-nowrap transition-colors duration-150",
                  categoryFilter === cat.id
                    ? "text-cyber-text font-medium"
                    : "text-cyber-muted hover:text-cyber-text",
                ].join(" ")}
              >
                {cat.label}
                <span className="ml-1.5 text-xs text-cyber-faint font-normal">{cat.skill_count}</span>
                {categoryFilter === cat.id && (
                  <span className="absolute bottom-0 left-2 right-2 h-[1.5px] bg-cyber-text" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Controls ── */}
      <div className="mb-7 flex flex-col gap-3 sm:flex-row sm:items-center">
        <SearchBar value={query} onChange={setQuery} className="flex-1" />

        <div className="flex gap-2">
          {/* Visibility filter */}
          <div className="relative">
            <select
              value={visibilityFilter}
              onChange={(e) => setVisibilityFilter(e.target.value)}
              className="
                appearance-none bg-white border border-cyber-border text-cyber-muted
                px-4 py-2.5 pr-8 text-sm rounded-lg outline-none
                hover:border-cyber-dim hover:text-cyber-text transition-colors cursor-pointer
                focus:border-cyber-dim
              "
            >
              {VISIBILITY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-cyber-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          {/* Level filter */}
          <div className="relative">
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="
                appearance-none bg-white border border-cyber-border text-cyber-muted
                px-4 py-2.5 pr-8 text-sm rounded-lg outline-none
                hover:border-cyber-dim hover:text-cyber-text transition-colors cursor-pointer
                focus:border-cyber-dim
              "
            >
              {LEVEL_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-cyber-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
      </div>

      {/* ── Loading ── */}
      {loading && (
        <div className="flex flex-col items-center justify-center gap-3 py-24">
          <Loader2 className="h-5 w-5 animate-spin text-cyber-faint" />
          <span className="text-sm text-cyber-faint">Loading skills...</span>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div className="flex flex-col items-center gap-4 border border-red-200 bg-red-50 rounded-xl p-10 text-center">
          <AlertCircle className="h-8 w-8 text-cyber-pink" />
          <p className="text-sm font-medium text-cyber-pink">{error}</p>
          <button onClick={() => fetchPage(false)} className="btn-cyber text-sm">
            Retry
          </button>
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center gap-3 border border-dashed border-cyber-border rounded-xl p-16 text-center">
          <Inbox className="h-10 w-10 text-cyber-faint" />
          <p className="text-sm text-cyber-muted">
            {isFiltered ? "No skills match your filters" : "No skills registered yet"}
          </p>
          {isFiltered && (
            <button
              onClick={() => { setQuery(""); setLevelFilter("all"); setCategoryFilter("all"); }}
              className="text-sm text-cyber-cyan hover:underline underline-offset-2"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* ── Grid ── */}
      {!loading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((skill) => (
            <SkillCard key={skill.id} skill={skill} />
          ))}
        </div>
      )}

      {/* ── Load more ── */}
      {hasMore && !query && levelFilter === "all" && categoryFilter === "all" && (
        <div className="mt-10 flex justify-center">
          <button
            onClick={() => fetchPage(true, cursor)}
            className="btn-cyber-ghost text-sm"
          >
            Load more skills
          </button>
        </div>
      )}
    </div>
  );
}
