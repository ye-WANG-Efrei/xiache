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
  placeholder = "Search skills by name, description, or tags...",
  className,
}: SearchBarProps) {
  const handleClear = useCallback(() => onChange(""), [onChange]);

  return (
    <div className={clsx("relative w-full", className)}>
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-cyber-faint" />

      <input
        type="search"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={clsx(
          "w-full bg-white border border-cyber-border",
          "py-2.5 pl-10 pr-10",
          "text-sm text-cyber-text placeholder:text-cyber-faint",
          "outline-none transition-all duration-150 rounded-lg",
          "hover:border-cyber-dim",
          "focus:border-cyber-dim",
        )}
      />

      {value && (
        <button
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-cyber-faint hover:text-cyber-muted transition-colors"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
}
