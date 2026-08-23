import { InjectionToken } from '@angular/core';

/** 「実行月」の算出に使う現在日。テストから固定値を注入できるようにする
 *  (docs/P006-test-plan.md §6.1)。 */
export const CURRENT_DATE = new InjectionToken<() => Date>('CURRENT_DATE', {
  providedIn: 'root',
  factory: () => () => new Date(),
});

/** ローカル日付を YYYY-MM-DD にする。toISOString は UTC に寄るため使わない。 */
export function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/** 実行月の 1 日と末日 (うるう年・月ごとの日数を含む)。 */
export function monthRange(now: Date): { from: string; to: string } {
  const first = new Date(now.getFullYear(), now.getMonth(), 1);
  // 翌月の 0 日目 = 当月の末日
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { from: toDateString(first), to: toDateString(last) };
}
