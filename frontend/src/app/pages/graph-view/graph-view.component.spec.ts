import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';

import { MetricsResponse } from '../../models/api.models';
import { GraphViewComponent, formatTime } from './graph-view.component';

const CATALOG = {
  groups: [
    { groupId: 'MG-CPU', title: 'CPU 使用率', description: 'CPU の内訳。', keyLabel: 'CPU', metrics: [] },
    { groupId: 'MG-DISK', title: 'ディスク I/O', description: 'デバイス別。', keyLabel: 'DEV', metrics: [] },
  ],
};

const METRICS: MetricsResponse = {
  fileId: 'c2FyMjM',
  fileName: 'sar23',
  kind: 'sar',
  date: '2026-08-23',
  hostname: 'www4250uj',
  kernel: '6.8.0-106-generic',
  arch: 'x86_64',
  cpuCount: 3,
  groups: [
    {
      groupId: 'MG-CPU',
      keyLabel: 'CPU',
      timestamps: ['2026-08-23T00:10:09', '2026-08-23T00:20:12'],
      series: [{ key: 'all', metric: '%usr', unit: '%', values: [2.07, 2.08] }],
    },
    {
      groupId: 'MG-DISK',
      keyLabel: 'DEV',
      timestamps: ['2026-08-23T00:10:09', '2026-08-23T00:20:12'],
      series: [
        { key: 'vda', metric: 'tps', unit: null, values: [1, 2] },
        { key: 'vda', metric: 'await', unit: 'ms', values: [3, 4] },
      ],
    },
  ],
};

describe('SC-02 GraphViewComponent', () => {
  let fixture: ComponentFixture<GraphViewComponent>;
  let http: HttpTestingController;

  function setup() {
    TestBed.configureTestingModule({
      imports: [GraphViewComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ fileId: 'c2FyMjM' }) } },
        },
        { provide: Router, useValue: { navigate: jasmine.createSpy('navigate') } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(GraphViewComponent);
  }

  afterEach(() => {
    http.verify();
    TestBed.resetTestingModule();
  });

  function flushOk(metrics: MetricsResponse = METRICS) {
    fixture.detectChanges();
    http.expectOne('/api/metric-catalog').flush(CATALOG);
    http.expectOne('/api/log-files/c2FyMjM/metrics').flush(metrics);
    fixture.detectChanges();
  }

  it('ファイル名・種別・採取日が表示される', () => {
    setup();
    flushOk();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="file-name"]')?.textContent).toContain('sar23');
    expect(el.querySelector('[data-testid="meta"]')?.textContent).toContain('sar');
    expect(el.querySelector('[data-testid="meta"]')?.textContent).toContain('2026-08-23');
  });

  it('hostname が null のときその項目を表示しない', () => {
    setup();
    flushOk({ ...METRICS, hostname: null });
    expect(fixture.nativeElement.querySelector('[data-testid="hostname"]')).toBeNull();
  });

  it('見出しと説明がグラフ要素より前に現れる', () => {
    setup();
    flushOk();
    const block: HTMLElement = fixture.nativeElement.querySelector('.chart-block');
    const children = Array.from(block.children).map((c) => c.className);
    expect(children.indexOf('chart-title')).toBeLessThan(children.indexOf('chart-canvas'));
    expect(children.indexOf('chart-desc')).toBeLessThan(children.indexOf('chart-canvas'));
  });

  it('単位が混在するグループが複数のグラフに分割される', () => {
    setup();
    flushOk();
    const c = fixture.componentInstance;
    const disk = c.charts.filter((x) => x.groupId === 'MG-DISK');
    expect(disk.length).toBe(2);
    const cpu = c.charts.filter((x) => x.groupId === 'MG-CPU');
    expect(cpu.length).toBe(1);
  });

  it('エラー応答時に message と hint を表示する', () => {
    setup();
    fixture.detectChanges();
    http.expectOne('/api/metric-catalog').flush(CATALOG);
    http.expectOne('/api/log-files/c2FyMjM/metrics').flush(
      {
        error: {
          code: 'SADF_UNAVAILABLE',
          message: 'sadf が見つかりません。',
          detail: 'no sadf',
          hint: '同一日の sar ファイル (sar23) が存在します。',
        },
      },
      { status: 503, statusText: 'Service Unavailable' },
    );
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="error"]')?.textContent).toContain(
      'sadf が見つかりません。',
    );
    expect(el.querySelector('[data-testid="error-hint"]')?.textContent).toContain('sar23');
  });

  it('戻るボタンで / へ遷移する', () => {
    setup();
    flushOk();
    const router = TestBed.inject(Router);
    fixture.nativeElement.querySelector('[data-testid="back"]').click();
    expect(router.navigate).toHaveBeenCalledWith(['/']);
  });

  it('目盛りラベルが HH:mm 形式になる', () => {
    const label = formatTime(new Date(2026, 7, 23, 9, 5, 0).getTime());
    expect(label).toBe('09:05');
  });
});
