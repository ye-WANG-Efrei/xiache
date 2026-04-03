"use client";

// ---------------------------------------------------------------------------
// Unified diff parser
// ---------------------------------------------------------------------------

type LineType = "add" | "remove" | "context" | "file-new" | "file-old" | "hunk";

interface DiffLine {
  type: LineType;
  content: string;
  lineNumOld?: number;
  lineNumNew?: number;
}

interface DiffFile {
  fileOld: string;
  fileNew: string;
  lines: DiffLine[];
}

function parseFilename(raw: string): string {
  // "--- a/foo/bar.md" → "foo/bar.md"
  // "+++ b/foo/bar.md" → same
  // "/dev/null" → "(new file)"
  return raw
    .replace(/^--- (a\/)?/, "")
    .replace(/^\+\+\+ (b\/)?/, "")
    .replace("/dev/null", "(new file)");
}

function parseHunkHeader(line: string): [number, number] {
  const m = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
  return m ? [parseInt(m[1], 10), parseInt(m[2], 10)] : [1, 1];
}

export function parseDiff(diff: string): DiffFile[] {
  const files: DiffFile[] = [];
  let cur: DiffFile | null = null;
  let oldLine = 1;
  let newLine = 1;

  for (const raw of diff.split("\n")) {
    if (raw.startsWith("--- ")) {
      const file: DiffFile = {
        fileOld: parseFilename(raw),
        fileNew: "",
        lines: [],
      };
      files.push(file);
      cur = file;
      // reset counters
      oldLine = 1;
      newLine = 1;
    } else if (raw.startsWith("+++ ") && cur) {
      cur.fileNew = parseFilename(raw);
    } else if (raw.startsWith("@@ ") && cur) {
      [oldLine, newLine] = parseHunkHeader(raw);
      cur.lines.push({ type: "hunk", content: raw });
    } else if (raw.startsWith("+") && cur) {
      cur.lines.push({ type: "add", content: raw.slice(1), lineNumNew: newLine });
      newLine++;
    } else if (raw.startsWith("-") && cur) {
      cur.lines.push({ type: "remove", content: raw.slice(1), lineNumOld: oldLine });
      oldLine++;
    } else if (raw.startsWith("\\")) {
      // "No newline at end of file" — skip
    } else if (cur) {
      cur.lines.push({
        type: "context",
        content: raw.startsWith(" ") ? raw.slice(1) : raw,
        lineNumOld: oldLine,
        lineNumNew: newLine,
      });
      oldLine++;
      newLine++;
    }
  }

  return files;
}

// ---------------------------------------------------------------------------
// Row styles
// ---------------------------------------------------------------------------

const ROW_STYLES: Record<LineType, string> = {
  add: "bg-green-50",
  remove: "bg-red-50",
  context: "bg-white",
  "file-new": "bg-gray-100",
  "file-old": "bg-gray-100",
  hunk: "bg-blue-50/60",
};

const TEXT_STYLES: Record<LineType, string> = {
  add: "text-green-800",
  remove: "text-red-800",
  context: "text-gray-700",
  "file-new": "text-gray-600",
  "file-old": "text-gray-600",
  hunk: "text-blue-600",
};

const GUTTER_STYLES: Record<LineType, string> = {
  add: "bg-green-100/70 border-green-200",
  remove: "bg-red-100/70 border-red-200",
  context: "bg-gray-50 border-gray-100",
  "file-new": "bg-gray-100 border-gray-200",
  "file-old": "bg-gray-100 border-gray-200",
  hunk: "bg-blue-100/50 border-blue-100",
};

const PREFIX: Record<LineType, string> = {
  add: "+",
  remove: "−",
  context: " ",
  "file-new": " ",
  "file-old": " ",
  hunk: " ",
};

const PREFIX_STYLE: Record<LineType, string> = {
  add: "text-green-500 font-bold",
  remove: "text-red-400 font-bold",
  context: "text-gray-300",
  "file-new": "",
  "file-old": "",
  hunk: "text-blue-400",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface DiffViewerProps {
  diff: string;
}

export function DiffViewer({ diff }: DiffViewerProps) {
  const files = parseDiff(diff);

  if (!diff.trim() || files.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-200 py-10 text-sm text-gray-400">
        No diff available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {files.map((file, fi) => {
        const label =
          file.fileNew && file.fileNew !== "(new file)"
            ? file.fileNew
            : file.fileOld;

        return (
          <div
            key={fi}
            className="overflow-hidden rounded-xl border border-gray-200 shadow-sm"
          >
            {/* File header */}
            <div className="flex items-center gap-2 border-b border-gray-200 bg-gray-100 px-4 py-2">
              <span className="font-mono text-xs font-semibold text-gray-700 break-all">
                {label}
              </span>
              {file.fileOld === "(new file)" && (
                <span className="ml-auto rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-700">
                  new file
                </span>
              )}
            </div>

            {/* Diff table */}
            <div className="overflow-x-auto">
              <table className="w-full border-collapse font-mono text-xs leading-5">
                <tbody>
                  {file.lines.map((line, li) => {
                    // Hunk header spans full width
                    if (line.type === "hunk") {
                      return (
                        <tr key={li} className={ROW_STYLES.hunk}>
                          <td
                            colSpan={3}
                            className="px-4 py-0.5 text-blue-500"
                          >
                            {line.content}
                          </td>
                        </tr>
                      );
                    }

                    const gutter = GUTTER_STYLES[line.type];
                    const row = ROW_STYLES[line.type];
                    const text = TEXT_STYLES[line.type];
                    const pre = PREFIX[line.type];
                    const preStyle = PREFIX_STYLE[line.type];

                    return (
                      <tr key={li} className={row}>
                        {/* Old line number */}
                        <td
                          className={`w-10 select-none border-r px-2 py-0.5 text-right text-gray-400 ${gutter}`}
                        >
                          {line.type !== "add"
                            ? (line.lineNumOld ?? "")
                            : ""}
                        </td>
                        {/* New line number */}
                        <td
                          className={`w-10 select-none border-r px-2 py-0.5 text-right text-gray-400 ${gutter}`}
                        >
                          {line.type !== "remove"
                            ? (line.lineNumNew ?? "")
                            : ""}
                        </td>
                        {/* Content */}
                        <td
                          className={`px-4 py-0.5 ${text} whitespace-pre`}
                        >
                          <span className={`mr-2 ${preStyle}`}>{pre}</span>
                          {line.content}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
