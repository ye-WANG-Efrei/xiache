"use client";

import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { Tag, GitBranch, User, ArrowUpRight } from "lucide-react";
import { type RecordMetadataItem } from "@/lib/api";
import { clsx } from "clsx";

interface SkillCardProps {
  skill: RecordMetadataItem;
  className?: string;
}

const LEVEL_STYLE: Record<string, { text: string; bg: string; border: string }> = {
  workflow:   { text: "text-sky-700",    bg: "bg-sky-50",    border: "border-sky-200" },
  tool_guide: { text: "text-amber-700",  bg: "bg-amber-50",  border: "border-amber-200" },
  reference:  { text: "text-stone-600",  bg: "bg-stone-100", border: "border-stone-200" },
};

const ORIGIN_STYLE: Record<string, { text: string; bg: string; border: string }> = {
  imported: { text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  captured: { text: "text-amber-700",   bg: "bg-amber-50",   border: "border-amber-200" },
  derived:  { text: "text-orange-700",  bg: "bg-orange-50",  border: "border-orange-200" },
  fixed:    { text: "text-red-700",     bg: "bg-red-50",     border: "border-red-200" },
};

export function SkillCard({ skill, className }: SkillCardProps) {
  const lvl = LEVEL_STYLE[skill.level] ?? LEVEL_STYLE.reference;
  const ori = ORIGIN_STYLE[skill.origin] ?? { text: "text-stone-600", bg: "bg-stone-100", border: "border-stone-200" };

  return (
    <Link
      href={`/skills/${encodeURIComponent(skill.id)}`}
      className={clsx(
        "group relative block bg-white border border-cyber-border rounded-xl p-5",
        "transition-all duration-200",
        "hover:border-cyber-dim hover:shadow-lg",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <h3 className={clsx(
            "font-display font-semibold text-xl leading-snug truncate",
            "text-cyber-text group-hover:text-cyber-yellow transition-colors duration-150"
          )}>
            {skill.name}
          </h3>
          <p className="mt-0.5 font-mono text-[10px] text-cyber-faint truncate">
            {skill.id}
          </p>
        </div>
        <ArrowUpRight
          className="h-4 w-4 text-cyber-faint group-hover:text-cyber-cyan flex-shrink-0 mt-1 transition-colors duration-150"
        />
      </div>

      {/* Description */}
      {skill.description && (
        <p className="text-sm text-cyber-muted line-clamp-2 leading-relaxed mb-3">
          {skill.description}
        </p>
      )}

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className={clsx(
          "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border",
          lvl.text, lvl.bg, lvl.border
        )}>
          {skill.level}
        </span>
        <span className={clsx(
          "inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border",
          ori.text, ori.bg, ori.border
        )}>
          {skill.origin}
        </span>
        {skill.category && (
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border border-cyber-cyan/40 text-cyber-cyan bg-cyber-cyan-dim">
            {skill.category}
          </span>
        )}
        {skill.visibility !== "public" && (
          <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded border border-stone-200 text-stone-500 bg-stone-100">
            {skill.visibility}
          </span>
        )}
      </div>

      {/* Tags */}
      {skill.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {skill.tags.slice(0, 5).map((tag) => (
            <span key={tag} className="chip-tag">
              <Tag className="h-2.5 w-2.5" />
              {tag}
            </span>
          ))}
          {skill.tags.length > 5 && (
            <span className="text-xs text-cyber-faint self-center">
              +{skill.tags.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-cyber-faint border-t border-cyber-border pt-2.5 mt-auto">
        <span className="flex items-center gap-1">
          <User className="h-3 w-3" />
          {skill.created_by || "unknown"}
        </span>
        <span className="flex items-center gap-1">
          <GitBranch className="h-3 w-3" />
          {skill.parent_skill_ids.length > 0
            ? `${skill.parent_skill_ids.length} parent${skill.parent_skill_ids.length > 1 ? "s" : ""}`
            : "root"}
        </span>
        <span>
          {formatDistanceToNow(new Date(skill.created_at), { addSuffix: true })}
        </span>
      </div>
    </Link>
  );
}
