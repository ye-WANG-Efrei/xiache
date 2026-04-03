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

// Level → accent color token
const LEVEL_STYLE: Record<string, { border: string; text: string; bg: string }> = {
  workflow:   { border: "border-cyber-cyan",   text: "text-cyber-cyan",   bg: "bg-cyber-cyan-dim" },
  tool_guide: { border: "border-cyber-yellow", text: "text-cyber-yellow", bg: "bg-cyber-yellow-dim" },
  reference:  { border: "border-cyber-muted",  text: "text-cyber-muted",  bg: "bg-cyber-card" },
};

const ORIGIN_STYLE: Record<string, { text: string; bg: string; border: string }> = {
  imported: { text: "text-cyber-green",  bg: "bg-cyber-green bg-opacity-10",  border: "border-cyber-green border-opacity-30" },
  captured: { text: "text-cyber-yellow", bg: "bg-cyber-yellow-dim",           border: "border-cyber-yellow border-opacity-30" },
  derived:  { text: "text-cyber-orange", bg: "bg-cyber-orange bg-opacity-10", border: "border-cyber-orange border-opacity-30" },
  fixed:    { text: "text-cyber-pink",   bg: "bg-cyber-pink-dim",             border: "border-cyber-pink border-opacity-30" },
};

export function SkillCard({ skill, className }: SkillCardProps) {
  const lvl = LEVEL_STYLE[skill.level] ?? LEVEL_STYLE.reference;
  const ori = ORIGIN_STYLE[skill.origin] ?? { text: "text-cyber-muted", bg: "bg-cyber-card", border: "border-cyber-border" };

  return (
    <Link
      href={`/skills/${encodeURIComponent(skill.record_id)}`}
      className={clsx(
        // Base
        "group relative block bg-cyber-card border border-cyber-border",
        "p-5 transition-all duration-200",
        // Clipped corners
        "clip-corners-lg",
        // Hover: neon border + glow
        "hover:border-cyber-cyan hover:glow-cyan",
        className
      )}
    >
      {/* Corner bracket decoration */}
      <span className="absolute top-0 left-0 w-3 h-3 border-t border-l border-cyber-cyan opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
      <span className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-cyber-yellow opacity-0 group-hover:opacity-100 transition-opacity duration-200" />

      {/* Level accent line */}
      <div className={clsx("absolute top-0 left-0 right-0 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-200", lvl.border.replace("border-", "bg-"))} />

      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <h3 className={clsx(
            "font-display font-bold text-base tracking-wide truncate",
            "text-cyber-text group-hover:text-cyber-yellow transition-colors duration-150"
          )}>
            {skill.name || skill.record_id}
          </h3>
          <p className="mt-0.5 font-mono text-[10px] text-cyber-faint truncate">
            {skill.record_id}
          </p>
        </div>
        <ArrowUpRight
          className="h-4 w-4 text-cyber-faint group-hover:text-cyber-cyan flex-shrink-0 mt-0.5 transition-colors duration-150"
        />
      </div>

      {/* Description */}
      {skill.description && (
        <p className="text-xs text-cyber-muted line-clamp-2 leading-relaxed mb-3">
          {skill.description}
        </p>
      )}

      {/* Badges */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {/* Level */}
        <span
          className={clsx(
            "inline-flex items-center px-2 py-0.5 text-[10px] font-mono font-medium tracking-wider border",
            lvl.text, lvl.bg, lvl.border,
          )}
          style={{ clipPath: "polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)" }}
        >
          {skill.level.toUpperCase()}
        </span>
        {/* Origin */}
        <span
          className={clsx(
            "inline-flex items-center px-2 py-0.5 text-[10px] font-mono font-medium tracking-wider border",
            ori.text, ori.bg, ori.border,
          )}
          style={{ clipPath: "polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)" }}
        >
          {skill.origin.toUpperCase()}
        </span>
        {/* Visibility */}
        {skill.visibility !== "public" && (
          <span
            className="inline-flex items-center px-2 py-0.5 text-[10px] font-mono text-cyber-muted border border-cyber-border bg-cyber-dark"
            style={{ clipPath: "polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)" }}
          >
            {skill.visibility.toUpperCase()}
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
            <span className="font-mono text-[10px] text-cyber-faint self-center">
              +{skill.tags.length - 5}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] font-mono text-cyber-faint border-t border-cyber-border pt-2.5 mt-auto">
        <span className="flex items-center gap-1">
          <User className="h-2.5 w-2.5" />
          {skill.created_by || "unknown"}
        </span>
        <span className="flex items-center gap-1">
          <GitBranch className="h-2.5 w-2.5" />
          {skill.parent_skill_ids.length > 0
            ? `${skill.parent_skill_ids.length}p`
            : "root"}
        </span>
        <span className="text-cyber-faint">
          {formatDistanceToNow(new Date(skill.created_at), { addSuffix: true })}
        </span>
      </div>
    </Link>
  );
}
