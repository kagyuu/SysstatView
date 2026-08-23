/** バックエンド API の応答に対応する型 (docs/P002-frontend-spec.md §5)。
 *  フィールド名はバックエンドと同じ camelCase。 */

export type LogFileKind = 'sa' | 'sar';

export interface LogFileInfo {
  fileId: string;
  fileName: string;
  kind: LogFileKind;
  date: string;
  sizeBytes: number;
  hostname: string | null;
}

export interface LogFileListResponse {
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
  items: LogFileInfo[];
}

export interface Series {
  key: string | null;
  metric: string;
  unit: string | null;
  values: (number | null)[];
}

export interface MetricGroup {
  groupId: string;
  keyLabel: string | null;
  timestamps: string[];
  series: Series[];
}

export interface MetricsResponse {
  fileId: string;
  fileName: string;
  kind: LogFileKind;
  date: string;
  hostname: string | null;
  kernel: string | null;
  arch: string | null;
  cpuCount: number | null;
  groups: MetricGroup[];
}

export interface MetricDefInfo {
  name: string;
  unit: string | null;
  description: string;
}

export interface GroupDefInfo {
  groupId: string;
  title: string;
  description: string;
  keyLabel: string | null;
  metrics: MetricDefInfo[];
}

export interface MetricCatalogResponse {
  groups: GroupDefInfo[];
}

export interface HealthResponse {
  status: string;
  logDir: string;
  sadfAvailable: boolean;
  sadfVersion: string | null;
  readableFileCount: number;
  unreadableFileCount: number;
}

/** docs/P002-frontend-spec.md §5.1 のエラー形式。 */
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly detail: string | null = null,
    readonly hint: string | null = null,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
