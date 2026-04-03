"use client";

import { useCallback } from "react";
import { Search, X } from "lucide-react";
import { clsx } from "clsx";

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({
  value,
  onChange,
  placeholder = "SEARCH SKILLS BY NAME, DESCRIPTION, OR TAGS...",
  className,
}: SearchBarProps) {
  const handleClear = useCallback(() => onChange(""), [onChange]);

  return (
    <div className={clsx("relative w-full group", className)}>
      {/* Corner accents */}
      <span className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 border-cyber-cyan opacity-40 group-focus-within:opacity-100 transition-opacity z-10 pointer-events-none" />
      <span className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 border-cyber-cyan opacity-40 group-focus-within:opacity-100 transition-opacity z-10 pointer-events-none" />

      {/* Search icon */}
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-cyber-faint group-focus-within:text-cyber-cyan transition-colors z-10" />

      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={clsx(
          "w-full bg-cyber-card border border-cyber-border",
          "py-2.5 pl-10 pr-10",
          "font-mono text-xs text-cyber-text placeholder:text-cyber-faint placeholder:tracking-wider",
          "outline-none transition-all duration-150",
          "hover:border-cyber-dim",
          "focus:border-cyber-cyan focus:glow-cyan",
        )}
        style={{ clipPath: "polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px)" }}
      />

      {/* Prompt prefix visual */}
      <span className="pointer-events-none absolute left-9 top-1/2 -translate-y-1/2 font-mono text-xs text-cyber-cyan opacity-60 select-none">
        {!value && ">_"}
      </span>

      {/* Clear button */}
      {value && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-faint hover:text-cyber-pink transition-colors z-10"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
