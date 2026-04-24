"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useRef, useEffect, useState } from "react";
import type { RecordResponse } from "@/lib/api";

// react-force-graph-2d uses browser APIs — client-only
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-64 items-center justify-center text-sm text-gray-400">
      Loading graph…
    </div>
  ),
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NodeKind = "ancestor" | "current" | "child" | "grandchild";

interface GraphNode {
  id: string;
  name: string;
  kind: NodeKind;
  // ForceGraph2D adds x/y at runtime
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
}

// ---------------------------------------------------------------------------
// Style maps
// ---------------------------------------------------------------------------

const NODE_COLOR: Record<NodeKind, string> = {
  ancestor:   "#B4B1AA",
  current:    "#1C1B18",
  child:      "#C3A97C",
  grandchild: "#8B7860",
};

const NODE_RADIUS: Record<NodeKind, number> = {
  ancestor: 5,
  current: 9,
  child: 6,
  grandchild: 4,
};

const LABEL_OFFSET: Record<NodeKind, number> = {
  ancestor: 8,
  current: 13,
  child: 9,
  grandchild: 7,
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RichRecord {
  name: string;
  id: string;
  parent_skill_ids: string[];
}

interface LineageGraphProps {
  record: RecordResponse;
  /** All records keyed by id (UUID) — used to traverse ancestry and descendants. */
  allRecords: Record<string, RichRecord>;
}

// ---------------------------------------------------------------------------
// Graph builder
// ---------------------------------------------------------------------------

const MAX_DEPTH = 3;

function buildGraph(
  record: RecordResponse,
  allRecords: Record<string, RichRecord>
): { nodes: GraphNode[]; links: GraphLink[] } {
  const nodeMap = new Map<string, GraphNode>();

  const addNode = (id: string, kind: NodeKind) => {
    if (nodeMap.has(id)) return;
    const meta = allRecords[id];
    nodeMap.set(id, { id, name: meta?.name ?? id, kind });
  };

  // ── 1. Current
  addNode(record.id, "current");

  // ── 2. Ancestors: BFS upward
  const ancQueue: Array<{ id: string; depth: number }> = record.parent_skill_ids.map(
    (pid) => ({ id: pid, depth: 1 })
  );
  const ancVisited = new Set<string>([record.id]);

  while (ancQueue.length > 0) {
    const { id, depth } = ancQueue.shift()!;
    if (ancVisited.has(id) || depth > MAX_DEPTH) continue;
    ancVisited.add(id);
    addNode(id, "ancestor");
    const meta = allRecords[id];
    if (meta) {
      for (const pid of meta.parent_skill_ids) {
        ancQueue.push({ id: pid, depth: depth + 1 });
      }
    }
  }

  // ── 3. Descendants: BFS downward via reverse index
  const childrenOf = new Map<string, string[]>();
  for (const [id, meta] of Object.entries(allRecords)) {
    for (const pid of meta.parent_skill_ids) {
      if (!childrenOf.has(pid)) childrenOf.set(pid, []);
      childrenOf.get(pid)!.push(id);
    }
  }

  const descQueue: Array<{ id: string; depth: number }> = (
    childrenOf.get(record.id) ?? []
  ).map((cid) => ({ id: cid, depth: 1 }));
  const descVisited = new Set<string>([record.id]);

  while (descQueue.length > 0) {
    const { id, depth } = descQueue.shift()!;
    if (descVisited.has(id) || depth > MAX_DEPTH) continue;
    descVisited.add(id);
    addNode(id, depth === 1 ? "child" : "grandchild");
    if (depth < MAX_DEPTH) {
      for (const child of childrenOf.get(id) ?? []) {
        descQueue.push({ id: child, depth: depth + 1 });
      }
    }
  }

  // ── 4. Build links: for every node in graph, link from its parents (if also in graph)
  const linkSet = new Set<string>();
  const links: GraphLink[] = [];

  for (const nodeId of nodeMap.keys()) {
    const parentIds =
      nodeId === record.id
        ? record.parent_skill_ids
        : (allRecords[nodeId]?.parent_skill_ids ?? []);

    for (const pid of parentIds) {
      if (!nodeMap.has(pid)) continue;
      const key = `${pid}→${nodeId}`;
      if (linkSet.has(key)) continue;
      linkSet.add(key);
      links.push({ source: pid, target: nodeId });
    }
  }

  return { nodes: Array.from(nodeMap.values()), links };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LineageGraph({ record, allRecords }: LineageGraphProps) {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(600);

  // Auto-resize
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(() => {
      setWidth(el.clientWidth);
    });
    obs.observe(el);
    setWidth(el.clientWidth);
    return () => obs.disconnect();
  }, []);

  const { nodes, links } = useMemo(
    () => buildGraph(record, allRecords),
    [record, allRecords]
  );

  const handleNodeClick = useCallback(
    (node: object) => {
      const n = node as GraphNode;
      if (n.id !== record.id) {
        router.push(`/skills/${encodeURIComponent(n.id)}`);
      }
    },
    [record.id, router]
  );

  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const r = NODE_RADIUS[node.kind];
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const fontSize = Math.max(8, Math.min(11, 12 / globalScale));

      // Circle
      ctx.beginPath();
      ctx.arc(x, y, r, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLOR[node.kind];
      ctx.fill();

      // Ring for "current" node
      if (node.kind === "current") {
        ctx.strokeStyle = "#3b5bdb";
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Label
      const label =
        node.name.length > 22 ? node.name.slice(0, 20) + "…" : node.name;
      ctx.font = `${node.kind === "current" ? "600 " : ""}${fontSize}px Inter, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillStyle = node.kind === "current" ? "#1e293b" : "#475569";
      ctx.fillText(label, x, y + LABEL_OFFSET[node.kind]);
    },
    []
  );

  const isTrivial = nodes.length <= 1 && links.length === 0;

  if (isTrivial) {
    return (
      <div className="flex h-28 items-center justify-center rounded-xl border border-dashed border-gray-200 text-sm text-gray-400">
        Root skill — no lineage to display.
      </div>
    );
  }

  // Legend
  const LEGEND: Array<{ kind: NodeKind; label: string }> = [
    { kind: "ancestor", label: "Ancestor" },
    { kind: "current", label: "This skill" },
    { kind: "child", label: "Child" },
    { kind: "grandchild", label: "Grandchild" },
  ];
  const visibleKinds = new Set(nodes.map((n) => n.kind));

  return (
    <div>
      {/* Legend */}
      <div className="mb-3 flex flex-wrap gap-3">
        {LEGEND.filter((l) => visibleKinds.has(l.kind)).map(({ kind, label }) => (
          <span key={kind} className="flex items-center gap-1.5 text-xs text-gray-500">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: NODE_COLOR[kind] }}
            />
            {label}
          </span>
        ))}
        <span className="ml-auto text-xs text-gray-400">
          Click node to navigate
        </span>
      </div>

      {/* Graph */}
      <div
        ref={containerRef}
        className="overflow-hidden rounded-xl border border-gray-200 bg-gray-50 cursor-pointer"
        style={{ height: 340 }}
      >
        <ForceGraph2D
          graphData={{ nodes, links }}
          width={width}
          height={340}
          nodeLabel={(node) => {
            const n = node as GraphNode;
            return `${n.name}${n.kind !== "current" ? "\n(click to view)" : ""}`;
          }}
          nodeColor={(node) => NODE_COLOR[(node as GraphNode).kind]}
          nodeRelSize={6}
          linkColor={() => "#cbd5e1"}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkWidth={1.5}
          onNodeClick={handleNodeClick}
          nodeCanvasObject={(node, ctx, globalScale) =>
            paintNode(node as GraphNode, ctx, globalScale)
          }
          nodePointerAreaPaint={(node, color, ctx) => {
            const n = node as GraphNode;
            const r = NODE_RADIUS[n.kind] + 4; // larger hit area
            ctx.beginPath();
            ctx.arc(n.x ?? 0, n.y ?? 0, r, 0, 2 * Math.PI);
            ctx.fillStyle = color;
            ctx.fill();
          }}
          cooldownTicks={80}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.3}
        />
      </div>

      <p className="mt-2 text-right text-xs text-gray-400">
        Showing up to {MAX_DEPTH} levels of ancestry and descendants
      </p>
    </div>
  );
}
