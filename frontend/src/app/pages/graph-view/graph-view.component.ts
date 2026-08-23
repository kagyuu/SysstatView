import { CommonModule } from '@angular/common';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  QueryList,
  ViewChildren,
  inject,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import {
  Chart,
  LineController,
  LineElement,
  LinearScale,
  PointElement,
  Legend,
  Tooltip,
} from 'chart.js';
import { forkJoin } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { ApiError, MetricsResponse } from '../../models/api.models';
import { ChartSpec, buildCharts } from './chart-builder';

// 使う機能だけ登録する (バンドルを小さく保つ)。
Chart.register(LineController, LineElement, LinearScale, PointElement, Legend, Tooltip);

const PALETTE = [
  '#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed',
  '#0891b2', '#db2777', '#65a30d', '#4b5563', '#c2410c',
];

/** SC-02 グラフ表示画面 (docs/P002-frontend-spec.md §3)。 */
@Component({
  selector: 'app-graph-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './graph-view.component.html',
  styleUrl: './graph-view.component.scss',
})
export class GraphViewComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  meta: MetricsResponse | null = null;
  charts: ChartSpec[] = [];
  loading = true;
  errorMessage: string | null = null;
  errorDetail: string | null = null;
  errorHint: string | null = null;
  showDetail = false;

  @ViewChildren('canvasRef') canvases!: QueryList<ElementRef<HTMLCanvasElement>>;

  private readonly rendered = new Map<string, Chart>();
  private observer: IntersectionObserver | null = null;

  ngOnInit(): void {
    const fileId = this.route.snapshot.paramMap.get('fileId') ?? '';
    forkJoin({
      catalog: this.api.getMetricCatalog(),
      metrics: this.api.getMetrics(fileId),
    }).subscribe({
      next: ({ catalog, metrics }) => {
        this.meta = metrics;
        this.charts = buildCharts(metrics.groups, catalog.groups);
        this.loading = false;
        // ビューが更新された後に描画対象を監視し直す。
        queueMicrotask(() => this.observeAll());
      },
      error: (err: ApiError) => {
        this.errorMessage = err.message;
        this.errorDetail = err.detail;
        this.errorHint = err.hint;
        this.loading = false;
      },
    });
  }

  ngAfterViewInit(): void {
    this.canvases.changes.subscribe(() => this.observeAll());
    this.observeAll();
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    for (const chart of this.rendered.values()) {
      chart.destroy();
    }
    this.rendered.clear();
  }

  onBack(): void {
    // SC-01 側が SearchStateService から状態を復元する (REQ-F-014)。
    this.router.navigate(['/']);
  }

  /** 画面内に入ったグラフから順に描画する (REQ-N-005)。
   *  見出しと説明は最初から描画済みであり、ここでは canvas のみを対象にする。 */
  private observeAll(): void {
    if (!this.canvases) {
      return;
    }
    if (typeof IntersectionObserver === 'undefined') {
      // 利用できない環境では全グラフを即時描画にフォールバックする。
      this.canvases.forEach((ref) => this.renderChart(ref.nativeElement));
      return;
    }
    if (!this.observer) {
      this.observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) {
              this.renderChart(entry.target as HTMLCanvasElement);
              this.observer?.unobserve(entry.target);
            }
          }
        },
        { rootMargin: '200px' },
      );
    }
    this.canvases.forEach((ref) => this.observer?.observe(ref.nativeElement));
  }

  private renderChart(canvas: HTMLCanvasElement): void {
    const id = canvas.dataset['chartId'];
    if (!id || this.rendered.has(id)) {
      return;
    }
    const spec = this.charts.find((c) => c.id === id);
    if (!spec) {
      return;
    }
    const chart = new Chart(canvas, {
      type: 'line',
      data: {
        datasets: spec.series.map((s, i) => ({
          label: s.label,
          data: s.points,
          borderColor: PALETTE[i % PALETTE.length],
          backgroundColor: PALETTE[i % PALETTE.length],
          borderWidth: 1.2,
          pointRadius: 0,
          spanGaps: false, // null の点で線を途切れさせる
          tension: 0,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        parsing: false,
        normalized: true,
        interaction: { mode: 'nearest', intersect: false },
        scales: {
          // 線形軸を使う (ADR-006)。カテゴリ軸は点を等間隔に描いてしまい、
          // 収集の欠測が視覚的に潰れるため使わない。
          x: {
            type: 'linear',
            ticks: {
              maxTicksLimit: 12,
              callback: (value) => formatTime(Number(value)),
            },
          },
          y: {
            beginAtZero: true,
            title: spec.unit ? { display: true, text: spec.unit } : undefined,
          },
        },
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: { boxWidth: 10, font: { size: 10 } },
          },
          tooltip: {
            callbacks: {
              title: (items) => formatTime(Number(items[0]?.parsed.x)),
            },
          },
        },
      },
    });
    this.rendered.set(id, chart);
  }
}

export function formatTime(epochMs: number): string {
  if (!Number.isFinite(epochMs)) {
    return '';
  }
  const d = new Date(epochMs);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}
