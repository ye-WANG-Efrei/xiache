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
    workflow:   { text: "text-cyber-cyan",   border: "border-cyber-cyan",   bg: "bg-cyber-cyan-dim" },
    tool_guide: { text: "text-cyber-yellow", border: "border-cyber-yellow", bg: "bg-cyber-yellow-dim" },
    reference:  { text: "text-cyber-muted",  border: "border-cyber-border", bg: "bg-cyber-card" },
  },
  origin: {
    imported: { text: "text-cyber-green",  border: "border-cyber-green border-opacity-40",  bg: "bg-cyber-green bg-opacity-10" },
    captured: { text: "text-cyber-yellow", border: "border-cyber-yellow border-opacity-40", bg: "bg-cyber-yellow-dim" },
    derived:  { text: "text-cyber-orange", border: "border-cyber-orange border-opacity-40", bg: "bg-cyber-orange bg-opacity-10" },
    fixed:    { text: "text-cyber-pink",   border: "border-cyber-pink border-opacity-40",   bg: "bg-cyber-pink-dim" },
  },
  visibility: {
    public:     { text: "text-cyber-green",  border: "border-cyber-green border-opacity-40",  bg: "bg-cyber-green bg-opacity-10" },
    group_only: { text: "text-cyber-pink",   border: "border-cyber-pink border-opacity-40",   bg: "bg-cyber-pink-dim" },
  },
};

function CyberBadge({ type, value }: { type: "level" | "origin" | "visibility"; value: string }) {
  const s = BADGE[type]?.[value] ?? { text: "text-cyber-muted", border: "border-cyber-border", bg: "bg-cyber-card" };
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 text-xs font-mono font-medium tracking-wider border",
        s.text, s.border, s.bg
      )}
      style={{ clipPath: "polygon(5px 0,100% 0,100% calc(100% - 5px),calc(100% - 5px) 100%,0 100%,0 5px)" }}
    >
      {value.toUpperCase()}
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
              "relative flex items-center gap-1.5 px-4 py-2.5 text-xs font-display font-semibold tracking-widest transition-all duration-150",
              active === t.id
                ? "text-cyber-yellow"
                : "text-cyber-muted hover:text-cyber-text"
            )}
          >
            {t.icon}
            {t.label}
            {/* Active indicator */}
            {active === t.id && (
              <span
                className="absolute bottom-0 left-0 right-0 h-px bg-cyber-yellow"
                style={{ boxShadow: "0 0 8px rgba(255,230,0,0.6)" }}
              />
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
        "inline-flex items-center gap-1.5 px-3 py-1 font-mono text-xs transition-all duration-150 border",
        variant === "parent"
          ? "border-cyber-border text-cyber-muted bg-cyber-card hover:border-cyber-cyan hover:text-cyber-cyan"
          : "border-cyber-orange border-opacity-40 text-cyber-orange bg-cyber-orange bg-opacity-5 hover:border-opacity-80"
      )}
      style={{ clipPath: "polygon(5px 0,100% 0,100% calc(100% - 5px),calc(100% - 5px) 100%,0 100%,0 5px)" }}
    >
      {variant === "child" && <GitMerge className="h-3 w-3 opacity-60" />}
      {name ?? id}
    </Link>
  );
}

// ── Metadata row ──────────────────────────────────────────────────────────

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-cyber-border last:border-0">
      <span className="text-cyber-faint mt-0.5 flex-shrink-0">{icon}</span>
      <span className="label-cyber w-24 flex-shrink-0 mt-0.5">{label}</span>
      <span className="text-cyber-text text-xs font-mono min-w-0 break-all">{value}</span>
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
        for (const item of meta.items) map[item.record_id] = item;
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
          { name: r.name, record_id: r.record_id, parent_skill_ids: r.parent_skill_ids },
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
      const url = await defaultClient.downloadRecordUrl(record.record_id);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${record.record_id}.zip`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* browser shows error */ }
    finally { setDownloading(false); }
  };

  // ── Loading
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-32">
        <Loader2 className="h-7 w-7 animate-spin text-cyber-cyan" />
        <span className="font-mono text-xs text-cyber-muted tracking-widest animate-cyber-pulse">
          FETCHING SKILL DATA...
        </span>
      </div>
    );
  }

  // ── Error
  if (error || !record) {
    return (
      <div
        className="flex flex-col items-center gap-5 border border-cyber-pink bg-cyber-pink-dim p-14 text-center"
        style={{ clipPath: "polygon(14px 0,100% 0,100% calc(100% - 14px),calc(100% - 14px) 100%,0 100%,0 14px)" }}
      >
        <AlertCircle className="h-10 w-10 text-cyber-pink" style={{ filter: "drop-shadow(0 0 8px rgba(255,0,60,0.5))" }} />
        <p className="font-mono text-sm text-cyber-pink">{error ?? "SKILL NOT FOUND"}</p>
        <Link href="/" className="btn-cyber-ghost text-xs tracking-widest">
          BACK TO REGISTRY
        </Link>
      </div>
    );
  }

  const tabs: TabItem[] = [
    { id: "overview", label: "OVERVIEW", icon: <Info className="h-3 w-3" /> },
    {
      id: "lineage",
      label: `LINEAGE${children.length + record.parent_skill_ids.length > 0 ? ` (${children.length + record.parent_skill_ids.length})` : ""}`,
      icon: <Network className="h-3 w-3" />,
    },
    {
      id: "diff",
      label: "DIFF",
      icon: <FileDiff className="h-3 w-3" />,
      hidden: !record.content_diff,
    },
  ];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back nav */}
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1.5 font-mono text-xs text-cyber-muted hover:text-cyber-cyan transition-colors group"
      >
        <ArrowLeft className="h-3.5 w-3.5 group-hover:-translate-x-0.5 transition-transform" />
        BACK TO REGISTRY
      </Link>

      {/* ── Header card ── */}
      <div
        className="relative bg-cyber-card border border-cyber-border p-6 mb-2"
        style={{ clipPath: "polygon(16px 0,100% 0,100% calc(100% - 16px),calc(100% - 16px) 100%,0 100%,0 16px)" }}
      >
        {/* Top accent line */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-cyber-cyan via-cyber-yellow to-transparent" />

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <h1
              className="font-display font-bold text-2xl tracking-wide text-cyber-text break-words"
              style={{ textShadow: "0 0 20px rgba(0,212,255,0.15)" }}
            >
              {record.name || record.record_id}
            </h1>
            <p className="mt-1 font-mono text-[10px] text-cyber-faint break-all">
              &gt;_ {record.record_id}
            </p>
          </div>

          <button
            onClick={handleDownload}
            disabled={downloading}
            className="btn-cyber text-xs flex-shrink-0 disabled:opacity-40"
          >
            {downloading
              ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
              : <Download className="h-3.5 w-3.5" />
            }
            DOWNLOAD ZIP
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
          <p className="mt-4 text-sm text-cyber-muted leading-relaxed border-l-2 border-cyber-cyan border-opacity-30 pl-3">
            {record.description}
          </p>
        )}
      </div>

      {/* ── Tab content ── */}
      <div
        className="bg-cyber-card border border-cyber-border p-6"
        style={{ clipPath: "polygon(0 0,100% 0,100% calc(100% - 16px),calc(100% - 16px) 100%,0 100%)" }}
      >
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
            <div className="border border-cyber-border bg-cyber-dark p-4"
              style={{ clipPath: "polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px)" }}
            >
              <MetaRow
                icon={<User className="h-3.5 w-3.5" />}
                label="CREATED BY"
                value={record.created_by || "unknown"}
              />
              <MetaRow
                icon={<Calendar className="h-3.5 w-3.5" />}
                label="CREATED"
                value={
                  <span title={format(new Date(record.created_at), "PPPpp")}>
                    {formatDistanceToNow(new Date(record.created_at), { addSuffix: true })}
                  </span>
                }
              />
              <MetaRow
                icon={<Fingerprint className="h-3.5 w-3.5" />}
                label="FINGERPRINT"
                value={
                  <span title={record.content_fingerprint} className="text-cyber-cyan">
                    {record.content_fingerprint.slice(0, 20)}…
                  </span>
                }
              />
            </div>

            {/* Change summary */}
            {record.change_summary && (
              <div
                className="bg-cyber-dark border border-cyber-dim p-4"
                style={{ clipPath: "polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px)" }}
              >
                <p className="label-cyber mb-2">CHANGE SUMMARY</p>
                <p className="text-sm text-cyber-text">{record.change_summary}</p>
              </div>
            )}

            {/* Lineage quick summary */}
            {(record.parent_skill_ids.length > 0 || children.length > 0) && (
              <div>
                <p className="label-cyber mb-2">LINEAGE</p>
                <div className="flex flex-wrap gap-3 text-xs font-mono text-cyber-muted">
                  {record.parent_skill_ids.length > 0 && (
                    <span className="flex items-center gap-1.5">
                      <GitBranch className="h-3 w-3 text-cyber-cyan" />
                      <span className="text-cyber-cyan">{record.parent_skill_ids.length}</span> parent{record.parent_skill_ids.length !== 1 ? "s" : ""}
                    </span>
                  )}
                  {children.length > 0 && (
                    <span className="flex items-center gap-1.5">
                      <GitMerge className="h-3 w-3 text-cyber-orange" />
                      <span className="text-cyber-orange">{children.length}</span> child{children.length !== 1 ? "ren" : ""}
                    </span>
                  )}
                  <button
                    onClick={() => setActiveTab("lineage")}
                    className="text-cyber-yellow hover:underline font-semibold"
                  >
                    VIEW GRAPH →
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
                <p className="label-cyber mb-2">PARENTS</p>
                <div className="flex flex-wrap gap-2">
                  {record.parent_skill_ids.map((pid) => (
                    <SkillChip key={pid} id={pid} name={allRecords[pid]?.name} variant="parent" />
                  ))}
                </div>
              </div>
            )}

            {children.length > 0 && (
              <div>
                <p className="label-cyber mb-2">CHILDREN ({children.length})</p>
                <div className="flex flex-wrap gap-2">
                  {children.map((c) => (
                    <SkillChip key={c.record_id} id={c.record_id} name={c.name} variant="child" />
                  ))}
                </div>
              </div>
            )}

            {record.parent_skill_ids.length === 0 && children.length === 0 && (
              <div
                className="flex items-center justify-center border border-dashed border-cyber-border py-10"
                style={{ clipPath: "polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px)" }}
              >
                <span className="font-mono text-sm text-cyber-faint">
                  &gt;_ ROOT SKILL — NO LINEAGE
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
