import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ApiError } from '../models/api.models';
import { ApiService } from './api.service';

describe('ApiService', () => {
  let api: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('listLogFiles が正しいクエリで /api/log-files を呼ぶ', () => {
    api.listLogFiles('2026-08-01', '2026-08-31', 2, 10).subscribe();
    const req = http.expectOne((r) => r.url === '/api/log-files');
    expect(req.request.params.get('from')).toBe('2026-08-01');
    expect(req.request.params.get('to')).toBe('2026-08-31');
    expect(req.request.params.get('page')).toBe('2');
    expect(req.request.params.get('perPage')).toBe('10');
    req.flush({ page: 2, perPage: 10, totalItems: 0, totalPages: 0, items: [] });
  });

  it('エラー応答が ApiError に変換される', (done) => {
    api.getMetrics('x').subscribe({
      error: (e: ApiError) => {
        expect(e.code).toBe('FILE_NOT_FOUND');
        expect(e.message).toBe('見つかりません。');
        expect(e.hint).toBe('ヒント');
        done();
      },
    });
    http.expectOne('/api/log-files/x/metrics').flush(
      { error: { code: 'FILE_NOT_FOUND', message: '見つかりません。', detail: null, hint: 'ヒント' } },
      { status: 404, statusText: 'Not Found' },
    );
  });

  it('ネットワークエラーが規定のメッセージになる', (done) => {
    api.getHealth().subscribe({
      error: (e: ApiError) => {
        expect(e.code).toBe('NETWORK_ERROR');
        expect(e.message).toBe('バックエンドに接続できません。');
        done();
      },
    });
    http.expectOne('/api/health').error(new ProgressEvent('error'));
  });
});
