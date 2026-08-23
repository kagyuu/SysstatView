import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CURRENT_DATE } from '../../core/current-date';
import { SearchStateService } from '../../core/search-state.service';
import { LogFileInfo } from '../../models/api.models';
import { FileSearchComponent } from './file-search.component';

function makeItems(count: number, offset = 0): LogFileInfo[] {
  return Array.from({ length: count }, (_, i) => ({
    fileId: `id-${offset + i}`,
    fileName: `sar${String(offset + i + 1).padStart(2, '0')}`,
    kind: 'sar' as const,
    date: `2026-08-${String(offset + i + 1).padStart(2, '0')}`,
    sizeBytes: 100,
    hostname: 'www4250uj',
  }));
}

describe('SC-01 FileSearchComponent', () => {
  let fixture: ComponentFixture<FileSearchComponent>;
  let http: HttpTestingController;
  let now: Date;

  function setup(fixedDate: Date) {
    now = fixedDate;
    TestBed.configureTestingModule({
      imports: [FileSearchComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CURRENT_DATE, useValue: () => now },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(FileSearchComponent);
  }

  afterEach(() => {
    http.verify();
    TestBed.resetTestingModule();
  });

  function flushList(items: LogFileInfo[], totalItems = items.length, totalPages = 1, page = 1) {
    const req = http.expectOne((r) => r.url === '/api/log-files');
    req.flush({ page, perPage: 10, totalItems, totalPages, items });
    fixture.detectChanges();
    return req;
  }

  // --- 初期値: 実行月の 1 日と末日 ---

  it('初期値が実行月の1日と末日になる (31日月)', () => {
    setup(new Date(2026, 7, 15)); // 2026-08
    fixture.detectChanges();
    const c = fixture.componentInstance;
    expect(c.from).toBe('2026-08-01');
    expect(c.to).toBe('2026-08-31');
    flushList([]);
  });

  it('初期値が実行月の1日と末日になる (30日月)', () => {
    setup(new Date(2026, 3, 10)); // 2026-04
    fixture.detectChanges();
    expect(fixture.componentInstance.to).toBe('2026-04-30');
    flushList([]);
  });

  it('初期値が実行月の1日と末日になる (うるう年の2月)', () => {
    setup(new Date(2024, 1, 5)); // 2024-02
    fixture.detectChanges();
    expect(fixture.componentInstance.to).toBe('2024-02-29');
    flushList([]);
  });

  it('初期値が実行月の1日と末日になる (平年の2月)', () => {
    setup(new Date(2025, 1, 5)); // 2025-02
    fixture.detectChanges();
    expect(fixture.componentInstance.to).toBe('2025-02-28');
    flushList([]);
  });

  // --- バリデーション ---

  it('開始日が終了日より後ならメッセージを出しAPIを呼ばない', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList([]);

    const c = fixture.componentInstance;
    c.from = '2026-08-31';
    c.to = '2026-08-01';
    c.onSearch();
    fixture.detectChanges();

    expect(c.validationMessage).toBe('開始日は終了日以前の日付を指定してください。');
    http.expectNone((r) => r.url === '/api/log-files');
  });

  // --- 一覧・選択・ページング ---

  it('初期選択が先頭行になる', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList(makeItems(10), 18, 2);
    expect(fixture.componentInstance.selectedFileId).toBe('id-0');
  });

  it('ページ切り替え後も先頭行が選択される', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList(makeItems(10), 18, 2);

    fixture.componentInstance.onPage(2);
    const req = http.expectOne((r) => r.url === '/api/log-files');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ page: 2, perPage: 10, totalItems: 18, totalPages: 2, items: makeItems(8, 10) });
    fixture.detectChanges();

    expect(fixture.componentInstance.page).toBe(2);
    expect(fixture.componentInstance.selectedFileId).toBe('id-10');
  });

  it('検索実行で1ページ目に戻る', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList(makeItems(10), 18, 2);

    fixture.componentInstance.onPage(2);
    http
      .expectOne((r) => r.url === '/api/log-files')
      .flush({ page: 2, perPage: 10, totalItems: 18, totalPages: 2, items: makeItems(8, 10) });
    fixture.detectChanges();

    fixture.componentInstance.onSearch();
    const req = http.expectOne((r) => r.url === '/api/log-files');
    expect(req.request.params.get('page')).toBe('1');
    req.flush({ page: 1, perPage: 10, totalItems: 18, totalPages: 2, items: makeItems(10) });
    fixture.detectChanges();
  });

  it('0件のときテーブルを表示せず表示ボタンが非活性', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList([], 0, 0);

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="file-table"]')).toBeNull();
    expect(el.querySelector('[data-testid="empty"]')?.textContent).toContain(
      '該当するログファイルがありません',
    );
    const show = el.querySelector<HTMLButtonElement>('[data-testid="show"]');
    expect(show?.disabled).toBeTrue();
  });

  it('1ページ目で前へ、最終ページで次へが非活性', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList(makeItems(10), 18, 2);

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector<HTMLButtonElement>('[data-testid="prev"]')?.disabled).toBeTrue();
    expect(el.querySelector<HTMLButtonElement>('[data-testid="next"]')?.disabled).toBeFalse();
  });

  it('総ページ数が12のときページ番号が12個すべて表示され省略記号が出ない', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    flushList(makeItems(10), 115, 12);

    const el: HTMLElement = fixture.nativeElement;
    const pager = el.querySelector('[data-testid="pager"]')!;
    expect(fixture.componentInstance.pageNumbers.length).toBe(12);
    expect(pager.textContent).not.toContain('…');
    // 現在ページ(1)はリンクにせず強調表示するため、リンクは 11 個
    expect(pager.querySelectorAll('button.page').length).toBe(11);
    expect(pager.querySelector('[data-testid="page-current"]')?.textContent?.trim()).toBe('1');
  });

  // --- 状態復元 ---

  it('保持状態がある場合は初期表示でAPIを呼ばず復元する', () => {
    setup(new Date(2026, 7, 15));
    const state = TestBed.inject(SearchStateService);
    state.save({
      from: '2026-08-05',
      to: '2026-08-20',
      items: makeItems(8, 10),
      page: 2,
      perPage: 10,
      totalItems: 18,
      totalPages: 2,
      selectedFileId: 'id-13',
    });

    fixture.detectChanges();
    http.expectNone((r) => r.url === '/api/log-files');

    const c = fixture.componentInstance;
    expect(c.from).toBe('2026-08-05');
    expect(c.to).toBe('2026-08-20');
    expect(c.page).toBe(2);
    expect(c.selectedFileId).toBe('id-13');
  });

  it('エラー応答時にメッセージを表示する', () => {
    setup(new Date(2026, 7, 15));
    fixture.detectChanges();
    http
      .expectOne((r) => r.url === '/api/log-files')
      .flush(
        { error: { code: 'INVALID_PARAMETER', message: '不正です。', detail: null, hint: null } },
        { status: 400, statusText: 'Bad Request' },
      );
    fixture.detectChanges();

    expect(fixture.componentInstance.errorMessage).toBe('不正です。');
  });
});
