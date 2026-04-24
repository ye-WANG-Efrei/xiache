"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Download,
  Tag,
  GitBranch,
  User,
  Calendar,
  Fingerprint,
  Loader2,
  AlertCircle,
  GitMerge,
  Network,
  FileDiff,
  Info,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import {
  defaultClient,
  type RecordResponse,
  type RecordMetadataItem,
} from "@/lib/api";
import { LineageGraph, type RichRecord } from "@/components/LineageGraph";
import { DiffViewer } from "@/components/DiffViewer";
import { clsx } from "clsx";

// ── Badge ──────────────────────────────────────────────────────────────────

const BADGE: Record<string, Record<string, { text: string; border: string; bg: string }>> = {
  level: {
    workflow:   { text: "text-sky-700",    border: "border-sky-200",    bg: "bg-sky-50" },
    tool_guide: { text: "text-amber-700",  border: "border-amber-200",  bg: "bg-amber-50" },
    reference:  { text: "text-stone-600",  border: "border-stone-200",  bg: "bg-stone-100" },
  },
  origin: {
    imported: { text: "text-emerald-700", border: "border-emerald-200", bg: "bg-emerald-50" },
    captured: { text: "text-amber-700",   border: "border-amber-200",   bg: "bg-amber-50" },
    derived:  { text: "text-orange-700",  border: "border-orange-200",  bg: "bg-orange-50" },
    fixed:    { text: "text-red-700",     border: "border-red-200",     bg: "bg-red-50" },
  },
  visibility: {
    public:     { text: "text-emerald-700", border: "border-emerald-200", bg: "bg-emerald-50" },
    group_only: { text: "text-stone-600",   border: "border-stone-200",   bg: "bg-stone-100" },
  },
};

function CyberBadge({ type, value }: { type: "level" | "origin" | "visibility"; value: string }) {
  const s = BADGE[type]?.[value] ?? { text: "text-stone-600", border: "border-stone-200", bg: "bg-stone-100" };
  return (
    <span className={clsx(
      "inline-flex items-center px-2.5 py-0.5 text-xs font-medium rounded border",
      s.text, s.border, s.bg
    )}>
      {value}
    </span>
  );
}

// ── Tab bar ────────────────────────────────────────────────────────────────

type Tab = "overview" | "lineage" | "diff";

interface TabItem {
  id: Tab;
  label: string;
  icon: React.ReactNode;
  hidden?: boolean;
}

function TabBar({ active, tabs, onChange }: { active: Tab; tabs: TabItem[]; onChange: (t: Tab) => void }) {
  return (
    <div className="flex gap-0 border-b border-cyber-border mb-6">
      {tabs
        .filter((t) => !t.hidden)
        .map((t) => (
          <button
            key={t.id}
            onClick={() => onChange(t.id)}
            className={clsx(
              "relative flex items-center gap-1.5 px-4 py-2.5 text-sm transition-all duration-150",
              active === t.id
                ? "text-cyber-text font-medium"
                : "text-cyber-muted hover:text-cyber-text"
            )}
          >
            {t.icon}
            {t.label}
            {active === t.id && (
              <span className="absolute bottom-0 left-0 right-0 h-px bg-cyber-text" />
            )}
          </button>
        ))}
    </div>
  );
}

// ── Skill link chip ────────────────────────────────────────────────────────

function SkillChip({ id, name, variant = "parent" }: { id: string; name?: string; variant?: "parent" | "child" }) {
  return (
    <Link
      href={`/skills/${encodeURIComponent(id)}`}
      className={clsx(
        "inline-flex items-center gap-1.5 px-3 py-1 text-sm transition-all duration-150 border rounded-lg",
        variant === "parent"
          ? "border-cyber-border text-cyber-muted bg-white hover:border-cyber-dim hover:text-cyber-text"
          : "border-orange-200 text-orange-700 bg-orange-50 hover:border-orange-300"
      )}
    >
      {variant === "child" && <GitMerge className="h-3 w-3 opacity-60" />}
      {name ?? id}
    </Link>
  );
}

// ── Metadata row ──────────────────────────────────────────────────────────

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-cyber-border last:border-0">
      <span className="text-cyber-faint mt-0.5 flex-shrink-0">{icon}</span>
      <span className="label-cyber w-28 flex-shrink-0 mt-0.5">{label}</span>
      <span className="text-cyber-text text-sm font-mono min-w-0 break-all">{value}</span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

export default function SkillDetailPage() {
  const params = useParams<{ id: string }>();
  const recordId = decodeURIComponent(params.id ?? "");

  const [record, setRecord] = useState<RecordResponse | null>(null);
  const [allRecords, setAllRecords] = useState<Record<string, RecordMetadataItem>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    if (!recordId) return;
    setLoading(true);
    setActiveTab("overview");
    Promise.all([
      defaultClient.getRecord(recordId),
      defaultClient.listRecordsMetadata({ limit: 500 }),
    ])
      .then(([rec, meta]) => {
        setRecord(rec);
        const map: Record<string, RecordMetadataItem> = {};
        for (const item of meta.items) map[item.id] = item;
        setAllRecords(map);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load skill");
      })
      .finally(() => setLoading(false));
  }, [recordId]);

  const richRecords = useMemo<Record<string, RichRecord>>(
    () =>
      Object.fromEntries(
        Object.entries(allRecords).map(([id, r]) => [
          id,
          { name: r.name, id: r.id, parent_skill_ids: r.parent_skill_ids },
        ])
      ),
    [allRecords]
  );

  const children = useMemo(
    () => Object.values(allRecords).filter((r) => r.parent_skill_ids.includes(recordId)),
    [allRecords, recordId]
  );

  const handleDownload = async () => {
    if (!record) return;
    setDownloading(true);
    try {
      const url = await defaultClient.downloadRecordUrl(record.id);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${record.name}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* browser shows error */ }
    finally { setDownloading(false); }
  };

  // ── Loading
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-32">
        <Loader2 className="h-5 w-5 animate-spin text-cyber-faint" />
        <span className="text-sm text-cyber-faint">Loading skill...</span>
      </div>
    );
  }

  // ── Error
  if (error || !record) {
    return (
      <div className="flex flex-col items-center gap-5 border border-red-200 bg-red-50 rounded-xl p-14 text-center">
        <AlertCircle className="h-10 w-10 text-cyber-pink" />
        <p className="text-sm text-cyber-pink font-medium">{error ?? "Skill not found"}</p>
        <Link href="/" className="btn-cyber-ghost text-sm">
          Back to registry
        </Link>
      </div>
    );
  }

  const tabs: TabItem[] = [
    { id: "overview", label: "Overview", icon: <Info className="h-3.5 w-3.5" /> },
    {
      id: "lineage",
      label: `Lineage${children.length + record.parent_skill_ids.length > 0 ? ` (${children.length + record.parent_skill_ids.length})` : ""}`,
      icon: <Network className="h-3.5 w-3.5" />,
    },
    {
      id: "diff",
      label: "Diff",
      icon: <FileDiff className="h-3.5 w-3.5" />,
      hidden: !record.content_diff,
    },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back nav */}
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-cyber-muted hover:text-cyber-text transition-colors group"
      >
        <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
        Back to registry
      </Link>

      {/* ── Header card ── */}
      <div className="bg-white border border-cyber-border rounded-xl p-6 mb-3"
        style={{ boxShadow: "0 1px 4px rgba(28,27,24,0.05)" }}>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="font-display font-semibold text-3xl text-cyber-text break-words">
              {record.name}
            </h1>
            <p className="mt-1 font-mono text-[10px] text-cyber-faint break-all">
              {record.id}
            </p>
          </div>

          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-cyber text-sm flex-shrink-0 disabled:opacity-40"
          >
            {downloading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <Download className="h-3.5 w-3.5" />
            }
            Download
          </button>
        </div>

        {/* Badges */}
        <div className="mt-4 flex flex-wrap gap-2">
          <CyberBadge type="level" value={record.level} />
          <CyberBadge type="origin" value={record.origin} />
          <CyberBadge type="visibility" value={record.visibility} />
        </div>

        {/* Description */}
        {record.description && (
          <p className="mt-4 text-sm text-cyber-muted leading-relaxed border-l-2 border-cyber-border pl-3">
            {record.description}
          </p>
        )}
      </div>

      {/* ── Tab content ── */}
      <div className="bg-white border border-cyber-border rounded-xl p-6"
        style={{ boxShadow: "0 1px 4px rgba(28,27,24,0.05)" }}>
        <TabBar active={activeTab} tabs={tabs} onChange={setActiveTab} />

        {/* ── Overview ── */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* Tags */}
            {record.tags.length > 0 && (
              <div>
                <p className="label-cyber mb-2">Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {record.tags.map((tag) => (
                    <span key={tag} className="chip-tag">
                      <Tag className="h-2.5 w-2.5" />
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="border border-cyber-border bg-cyber-dark rounded-lg p-4">
              <MetaRow
                icon={<User className="h-3.5 w-3.5" />}
                label="Created by"
                value={record.created_by || "unknown"}
              />
              <MetaRow
                icon={<Calendar className="h-3.5 w-3.5" />}
                label="Created"
                value={
                  <span title={format(new Date(record.created_at), "PPPpp")}>
                    {formatDistanceToNow(new Date(record.created_at), { addSuffix: true })}
                  </span>
                }
              />
              <MetaRow
                icon={<Fingerprint className="h-3.5 w-3.5" />}
                label="Fingerprint"
                value={
                  <span title={record.content_fingerprint} className="text-cyber-cyan">
                    {record.content_fingerprint.slice(0, 20)}…
                  </span>
                }
              />
            </div>

            {/* Change summary */}
            {record.change_summary && (
              <div className="bg-cyber-dark border border-cyber-border rounded-lg p-4">
                <p className="label-cyber mb-2">Change summary</p>
                <p className="text-sm text-cyber-text leading-relaxed">{record.change_summary}</p>
              </div>
            )}

            {/* Lineage quick summary */}
            {(record.parent_skill_ids.length > 0 || children.length > 0) && (
              <div>
                <p className="label-cyber mb-2">Lineage</p>
                <div className="flex flex-wrap gap-3 text-sm text-cyber-muted">
                  {record.parent_skill_ids.length > 0 && (
                    <span className="flex items-center gap-1.5">
                      <GitBranch className="h-3.5 w-3.5 text-cyber-cyan" />
                      <span className="font-medium text-cyber-text">{record.parent_skill_ids.length}</span>
                      {" "}parent{record.parent_skill_ids.length !== 1 ? "s" : ""}
                    </span>
                  )}
                  {children.length > 0 && (
                    <span className="flex items-center gap-1.5">
                      <GitMerge className="h-3.5 w-3.5 text-cyber-orange" />
                      <span className="font-medium text-cyber-text">{children.length}</span>
                      {" "}child{children.length !== 1 ? "ren" : ""}
                    </span>
                  )}
                  <button
                    onClick={() => setActiveTab("lineage")}
                    className="text-cyber-yellow font-medium hover:underline underline-offset-2"
                  >
                    View graph →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Lineage ── */}
        {activeTab === "lineage" && (
          <div className="space-y-6">
            <LineageGraph record={record} allRecords={richRecords} />

            {record.parent_skill_ids.length > 0 && (
              <div>
                <p className="label-cyber mb-2">Parents</p>
                <div className="flex flex-wrap gap-2">
                  {record.parent_skill_ids.map((pid) => (
                    <SkillChip key={pid} id={pid} name={allRecords[pid]?.name} variant="parent" />
                  ))}
                </div>
              </div>
            )}

            {children.length > 0 && (
              <div>
                <p className="label-cyber mb-2">Children ({children.length})</p>
                <div className="flex flex-wrap gap-2">
                  {children.map((c) => (
                    <SkillChip key={c.id} id={c.id} name={c.name} variant="child" />
                  ))}
                </div>
              </div>
            )}

            {record.parent_skill_ids.length === 0 && children.length === 0 && (
              <div className="flex items-center justify-center border border-dashed border-cyber-border rounded-lg py-10">
                <span className="text-sm text-cyber-faint">
                  Root skill — no lineage
                </span>
              </div>
            )}
          </div>
        )}

        {/* ── Diff ── */}
        {activeTab === "diff" && record.content_diff && (
          <DiffViewer diff={record.content_diff} />
        )}
      </div>
    </div>
  );
}
