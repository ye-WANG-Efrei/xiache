import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

// ---------------------------------------------------------------------------
// Types (mirrors backend schemas/api.py)
// ---------------------------------------------------------------------------

export interface ArtifactStats {
  file_count: number;
  total_size: number;
}

export interface StageArtifactResponse {
  artifact_id: string;
  stats: ArtifactStats;
}

export interface CreateRecordRequest {
  record_id: string;
  artifact_id: string;
  origin: string;
  visibility?: string;
  parent_skill_ids?: string[];
  tags?: string[];
  level?: string;
  created_by?: string;
  change_summary?: string;
  content_diff?: string;
}

export interface RecordResponse {
  record_id: string;
  artifact_id: string;
  name: string;
  description: string;
  origin: string;
  visibility: string;
  level: string;
  tags: string[];
  created_by: string;
  change_summary: string;
  content_diff: string | null;
  content_fingerprint: string;
  parent_skill_ids: string[];
  created_at: string;
  embedding?: number[] | null;
}

export interface RecordMetadataItem
  extends Omit<RecordResponse, "content_diff"> {}

export interface RecordMetadataResponse {
  items: RecordMetadataItem[];
  has_more: boolean;
  next_cursor: string | null;
  total: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
}

export interface SearchResult {
  record_id: string;
  name: string;
  description: string;
  origin: string;
  visibility: string;
  level: string;
  tags: string[];
  created_by: string;
  created_at: string;
  score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  count: number;
  search_type: "hybrid" | "fulltext";
}

// ---------------------------------------------------------------------------
// Evolutions
// ---------------------------------------------------------------------------

export interface ProposeEvolutionRequest {
  artifact_id: string;
  parent_skill_id?: string | null;
  origin: string; // fixed | derived | captured
  change_summary?: string;
  content_diff?: string | null;
  tags?: string[];
}

export interface EvaluationResult {
  passed: boolean;
  quality_score: number;
  notes: string;
  checks: Record<string, boolean>;
}

export interface EvolutionResponse {
  evolution_id: string;
  status: "pending" | "evaluating" | "accepted" | "rejected";
  proposed_name: string;
  proposed_desc: string;
  parent_skill_id: string | null;
  origin: string;
  proposed_by: string;
  proposed_at: string;
  evaluated_at: string | null;
  evaluation: EvaluationResult | null;
  result_record_id: string | null;
  change_summary: string;
  tags: string[];
  auto_accepted: boolean;
}

export interface EvolutionListResponse {
  items: EvolutionResponse[];
  total: number;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export class XiacheClient {
  private http: AxiosInstance;

  constructor(
    apiKey: string,
    baseURL: string = process.env.NEXT_PUBLIC_API_URL ?? ""
  ) {
    this.http = axios.create({
      baseURL: baseURL || "",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      timeout: 30_000,
    });
  }

  // Health
  async health(): Promise<HealthResponse> {
    const { data } = await this.http.get<HealthResponse>("/api/v1/health");
    return data;
  }

  // Stage artifact (multipart)
  async stageArtifact(files: File[]): Promise<StageArtifactResponse> {
    const form = new FormData();
    for (const f of files) {
      form.append("files", f, f.name);
    }
    const { data } = await this.http.post<StageArtifactResponse>(
      "/api/v1/artifacts/stage",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return data;
  }

  // Create record
  async createRecord(body: CreateRecordRequest): Promise<RecordResponse> {
    const { data } = await this.http.post<RecordResponse>(
      "/api/v1/records",
      body
    );
    return data;
  }

  // Get single record
  async getRecord(
    recordId: string,
    includeEmbedding = false
  ): Promise<RecordResponse> {
    const { data } = await this.http.get<RecordResponse>(
      `/api/v1/records/${encodeURIComponent(recordId)}`,
      { params: { include_embedding: includeEmbedding } }
    );
    return data;
  }

  // List records metadata (paginated)
  async listRecordsMetadata(opts?: {
    limit?: number;
    cursor?: string;
    includeEmbedding?: boolean;
    visibility?: string;
  }): Promise<RecordMetadataResponse> {
    const params: Record<string, unknown> = {};
    if (opts?.limit) params.limit = opts.limit;
    if (opts?.cursor) params.cursor = opts.cursor;
    if (opts?.includeEmbedding) params.include_embedding = true;
    if (opts?.visibility) params.visibility = opts.visibility;

    const { data } = await this.http.get<RecordMetadataResponse>(
      "/api/v1/records/metadata",
      { params }
    );
    return data;
  }

  // Download record as ZIP blob URL
  async downloadRecordUrl(recordId: string): Promise<string> {
    const { data } = await this.http.get(
      `/api/v1/records/${encodeURIComponent(recordId)}/download`,
      { responseType: "blob" }
    );
    return URL.createObjectURL(data as Blob);
  }

  // Search skills (server-side hybrid search)
  async search(
    query: string,
    opts?: { limit?: number }
  ): Promise<SearchResponse> {
    const { data } = await this.http.get<SearchResponse>("/api/v1/search", {
      params: { q: query, limit: opts?.limit ?? 20 },
    });
    return data;
  }

  // Fetch all pages of metadata (helper)
  async *listAllRecords(opts?: {
    includeEmbedding?: boolean;
    visibility?: string;
    pageSize?: number;
  }): AsyncGenerator<RecordMetadataItem[]> {
    let cursor: string | undefined;
    const limit = opts?.pageSize ?? 100;

    do {
      const page = await this.listRecordsMetadata({
        limit,
        cursor,
        includeEmbedding: opts?.includeEmbedding,
        visibility: opts?.visibility,
      });
      yield page.items;
      cursor = page.next_cursor ?? undefined;
    } while (cursor);
  }

  // ---------------------------------------------------------------------------
  // Evolutions
  // ---------------------------------------------------------------------------

  /** Propose a skill evolution (PR-like workflow). Returns 201 on success. */
  async proposeEvolution(
    body: ProposeEvolutionRequest
  ): Promise<EvolutionResponse> {
    const { data } = await this.http.post<EvolutionResponse>(
      "/api/v1/evolutions",
      body
    );
    return data;
  }

  /** Fetch the current status and evaluation details of an evolution. */
  async getEvolution(id: string): Promise<EvolutionResponse> {
    const { data } = await this.http.get<EvolutionResponse>(
      `/api/v1/evolutions/${encodeURIComponent(id)}`
    );
    return data;
  }

  /** List evolutions with optional filters. */
  async listEvolutions(opts?: {
    status?: "pending" | "evaluating" | "accepted" | "rejected";
    parent_skill_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<EvolutionListResponse> {
    const params: Record<string, unknown> = {};
    if (opts?.status) params.status = opts.status;
    if (opts?.parent_skill_id) params.parent_skill_id = opts.parent_skill_id;
    if (opts?.limit !== undefined) params.limit = opts.limit;
    if (opts?.offset !== undefined) params.offset = opts.offset;

    const { data } = await this.http.get<EvolutionListResponse>(
      "/api/v1/evolutions",
      { params }
    );
    return data;
  }

  /** Manually accept a pending evolution, creating a new SkillRecord. */
  async acceptEvolution(id: string): Promise<EvolutionResponse> {
    const { data } = await this.http.post<EvolutionResponse>(
      `/api/v1/evolutions/${encodeURIComponent(id)}/accept`
    );
    return data;
  }

  /** Reject a pending evolution with a human-readable reason. */
  async rejectEvolution(id: string, reason: string): Promise<EvolutionResponse> {
    const { data } = await this.http.post<EvolutionResponse>(
      `/api/v1/evolutions/${encodeURIComponent(id)}/reject`,
      { reason }
    );
    return data;
  }
}

// Default anonymous client (read-only in public mode, uses dev key from env)
export const defaultClient = new XiacheClient(
  process.env.NEXT_PUBLIC_API_KEY ?? "dev-key-for-testing"
);
