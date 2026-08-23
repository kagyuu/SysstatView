import { GroupDefInfo, MetricGroup } from '../../models/api.models';
import { buildCharts, toEpochMs } from './chart-builder';

const CATALOG: GroupDefInfo[] = [
  { groupId: 'MG-CPU', title: 'CPU 使用率', description: 'CPU の内訳。', keyLabel: 'CPU', metrics: [] },
  { groupId: 'MG-MEM', title: 'メモリ使用量', description: 'メモリの状況。', keyLabel: null, metrics: [] },
  { groupId: 'MG-DISK', title: 'ディスク I/O', description: 'デバイス別。', keyLabel: 'DEV', metrics: [] },
];

const TS = ['2026-08-23T00:10:09', '2026-08-23T00:20:12'];

function group(groupId: string, keyLabel: string | null, series: MetricGroup['series']): MetricGroup {
  return { groupId, keyLabel, timestamps: TS, series };
}

describe('chart-builder', () => {
  it('単位が1種類のグループは1グラフで見出しに単位を付けない', () => {
    const charts = buildCharts(
      [
        group('MG-CPU', 'CPU', [
          { key: 'all', metric: '%usr', unit: '%', values: [1, 2] },
          { key: 'all', metric: '%sys', unit: '%', values: [3, 4] },
        ]),
      ],
      CATALOG,
    );
    expect(charts.length).toBe(1);
    expect(charts[0].title).toBe('CPU 使用率');
    expect(charts[0].series.length).toBe(2);
  });

  it('単位が3種類のグループは3グラフに分割され見出しに単位が付く', () => {
    const charts = buildCharts(
      [
        group('MG-DISK', 'DEV', [
          { key: 'vda', metric: 'tps', unit: null, values: [1, 2] },
          { key: 'vda', metric: 'rkB/s', unit: 'KB/s', values: [3, 4] },
          { key: 'vda', metric: 'await', unit: 'ms', values: [5, 6] },
        ]),
      ],
      CATALOG,
    );
    expect(charts.length).toBe(3);
    for (const c of charts) {
      expect(c.title).toContain('ディスク I/O (');
    }
    // 出力順は単位キーの昇順 (単位なしを先頭に置く)。
    // ここで .sort() を掛けると null が文字列 "null" として末尾に回るため、
    // 実装が返す順序をそのまま検証する。
    expect(charts.map((c) => c.unit)).toEqual([null, 'KB/s', 'ms']);
  });

  it('単位なしの系列がひとまとまりになる', () => {
    const charts = buildCharts(
      [
        group('MG-MEM', null, [
          { key: null, metric: 'a', unit: null, values: [1, 2] },
          { key: null, metric: 'b', unit: null, values: [3, 4] },
          { key: null, metric: '%memused', unit: '%', values: [5, 6] },
        ]),
      ],
      CATALOG,
    );
    expect(charts.length).toBe(2);
    const noUnit = charts.find((c) => c.unit === null)!;
    expect(noUnit.series.length).toBe(2);
    expect(noUnit.title).toContain('単位なし');
  });

  it('系列名がキー付きは key / metric、キーなしは metric', () => {
    const charts = buildCharts(
      [
        group('MG-CPU', 'CPU', [{ key: 'all', metric: '%usr', unit: '%', values: [1, 2] }]),
        group('MG-MEM', null, [{ key: null, metric: 'kbmemfree', unit: 'KB', values: [1, 2] }]),
      ],
      CATALOG,
    );
    expect(charts[0].series[0].label).toBe('all / %usr');
    expect(charts[1].series[0].label).toBe('kbmemfree');
  });

  it('出力順がカタログ順に従う', () => {
    const charts = buildCharts(
      [
        group('MG-DISK', 'DEV', [{ key: 'vda', metric: 'tps', unit: null, values: [1, 2] }]),
        group('MG-CPU', 'CPU', [{ key: 'all', metric: '%usr', unit: '%', values: [1, 2] }]),
      ],
      CATALOG,
    );
    expect(charts.map((c) => c.groupId)).toEqual(['MG-CPU', 'MG-DISK']);
  });

  it('同一入力で2回呼んでも同じ順序になる', () => {
    const input = [
      group('MG-DISK', 'DEV', [
        { key: 'vda', metric: 'tps', unit: null, values: [1, 2] },
        { key: 'vda', metric: 'rkB/s', unit: 'KB/s', values: [3, 4] },
      ]),
    ];
    const a = buildCharts(input, CATALOG).map((c) => c.id);
    const b = buildCharts(input, CATALOG).map((c) => c.id);
    expect(a).toEqual(b);
  });

  it('X 値が epoch ミリ秒で実時間差に比例する', () => {
    const g: MetricGroup = {
      groupId: 'MG-CPU',
      keyLabel: 'CPU',
      // 10分3秒 → 19分51秒 と間隔が不均一
      timestamps: ['2026-08-23T00:10:09', '2026-08-23T00:20:12', '2026-08-23T00:40:00'],
      series: [{ key: 'all', metric: '%usr', unit: '%', values: [1, 2, 3] }],
    };
    const chart = buildCharts([g], CATALOG)[0];
    const xs = chart.series[0].points.map((p) => p.x);
    const d1 = xs[1] - xs[0];
    const d2 = xs[2] - xs[1];
    expect(d1).toBe(603 * 1000);
    expect(d2).toBe(1188 * 1000);
    // カテゴリ軸なら等間隔になるはずなので、差が異なることを確認する
    expect(d1).not.toBe(d2);
  });

  it('null の値がそのまま保持される', () => {
    const charts = buildCharts(
      [group('MG-CPU', 'CPU', [{ key: 'all', metric: '%usr', unit: '%', values: [1, null] }])],
      CATALOG,
    );
    expect(charts[0].series[0].points[1].y).toBeNull();
  });

  it('toEpochMs がローカル時刻として解釈する', () => {
    const ms = toEpochMs('2026-08-23T00:10:09');
    const d = new Date(ms);
    expect(d.getFullYear()).toBe(2026);
    expect(d.getMonth()).toBe(7);
    expect(d.getDate()).toBe(23);
    expect(d.getHours()).toBe(0);
    expect(d.getMinutes()).toBe(10);
    expect(d.getSeconds()).toBe(9);
  });
});
