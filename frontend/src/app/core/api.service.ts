import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import {
  ApiError,
  HealthResponse,
  LogFileListResponse,
  MetricCatalogResponse,
  MetricsResponse,
} from '../models/api.models';

/** API は常に相対パスで呼ぶ。同一オリジン構成のため (ADR-001)。 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  listLogFiles(
    from: string,
    to: string,
    page: number,
    perPage: number,
  ): Observable<LogFileListResponse> {
    const params = new HttpParams()
      .set('from', from)
      .set('to', to)
      .set('page', String(page))
      .set('perPage', String(perPage));
    return this.http
      .get<LogFileListResponse>('/api/log-files', { params })
      .pipe(catchError(toApiError));
  }

  getMetrics(fileId: string): Observable<MetricsResponse> {
    return this.http
      .get<MetricsResponse>(`/api/log-files/${encodeURIComponent(fileId)}/metrics`)
      .pipe(catchError(toApiError));
  }

  getMetricCatalog(): Observable<MetricCatalogResponse> {
    return this.http
      .get<MetricCatalogResponse>('/api/metric-catalog')
      .pipe(catchError(toApiError));
  }

  getHealth(): Observable<HealthResponse> {
    return this.http.get<HealthResponse>('/api/health').pipe(catchError(toApiError));
  }
}

function toApiError(err: HttpErrorResponse) {
  const body = err.error as { error?: { code: string; message: string; detail: string | null; hint: string | null } } | null;
  if (body && body.error && body.error.code) {
    const e = body.error;
    return throwError(() => new ApiError(e.code, e.message, e.detail ?? null, e.hint ?? null));
  }
  // ネットワークエラーなど、規定の形式で返ってこなかった場合。
  return throwError(
    () => new ApiError('NETWORK_ERROR', 'バックエンドに接続できません。', null, null),
  );
}
