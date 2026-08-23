import { Injectable } from '@angular/core';

import { LogFileInfo } from '../models/api.models';

/** SC-01 の画面状態 (docs/P002-frontend-spec.md §1.1)。 */
export interface SearchState {
  from: string;
  to: string;
  items: LogFileInfo[];
  page: number;
  perPage: number;
  totalItems: number;
  totalPages: number;
  selectedFileId: string | null;
}

/** SC-02 へ遷移して戻っても SC-01 の状態が失われないようにする (REQ-F-014)。
 *
 *  アプリケーションスコープで保持する。localStorage / sessionStorage は使わない
 *  (リロード耐性は要求されていない。docs/P002-frontend-spec.md §1.1 で ★ACCEPTED★)。 */
@Injectable({ providedIn: 'root' })
export class SearchStateService {
  private state: SearchState | null = null;

  hasState(): boolean {
    return this.state !== null;
  }

  save(state: SearchState): void {
    // 呼び出し側が後から書き換えても保持内容が変わらないよう複製する。
    this.state = { ...state, items: [...state.items] };
  }

  restore(): SearchState | null {
    if (this.state === null) {
      return null;
    }
    return { ...this.state, items: [...this.state.items] };
  }

  clear(): void {
    this.state = null;
  }
}
