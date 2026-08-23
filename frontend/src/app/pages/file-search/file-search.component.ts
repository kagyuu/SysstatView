import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { ApiService } from '../../core/api.service';
import { CURRENT_DATE, monthRange } from '../../core/current-date';
import { SearchStateService } from '../../core/search-state.service';
import { ApiError, LogFileInfo } from '../../models/api.models';

const PER_PAGE = 10;

/** SC-01 ログファイル検索・選択画面 (docs/P002-frontend-spec.md §2)。 */
@Component({
  selector: 'app-file-search',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './file-search.component.html',
  styleUrl: './file-search.component.scss',
})
export class FileSearchComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly state = inject(SearchStateService);
  private readonly router = inject(Router);
  private readonly now = inject(CURRENT_DATE);

  from = '';
  to = '';
  items: LogFileInfo[] = [];
  page = 1;
  readonly perPage = PER_PAGE;
  totalItems = 0;
  totalPages = 0;
  selectedFileId: string | null = null;

  loading = false;
  validationMessage: string | null = null;
  errorMessage: string | null = null;
  errorHint: string | null = null;

  ngOnInit(): void {
    const restored = this.state.restore();
    if (restored) {
      // 戻ってきた場合は API を再実行しない (docs/P002-frontend-spec.md §4.1)。
      this.from = restored.from;
      this.to = restored.to;
      this.items = restored.items;
      this.page = restored.page;
      this.totalItems = restored.totalItems;
      this.totalPages = restored.totalPages;
      this.selectedFileId = restored.selectedFileId;
      return;
    }
    const range = monthRange(this.now());
    this.from = range.from;
    this.to = range.to;
    this.fetch(1);
  }

  /** 検索ボタン。押下時は常に 1 ページ目へ戻す。 */
  onSearch(): void {
    if (!this.validate()) {
      return;
    }
    this.fetch(1);
  }

  onPage(page: number): void {
    if (page < 1 || page > this.totalPages || page === this.page || this.loading) {
      return;
    }
    this.fetch(page);
  }

  onShow(): void {
    if (!this.selectedFileId) {
      return;
    }
    this.persist();
    this.router.navigate(['/graph', this.selectedFileId]);
  }

  get pageNumbers(): number[] {
    // 省略表示 (…) は行わない (docs/P002-frontend-spec.md §2.3 の ★ACCEPTED★)。
    return Array.from({ length: this.totalPages }, (_, i) => i + 1);
  }

  get hasResults(): boolean {
    return this.items.length > 0;
  }

  get canShow(): boolean {
    return this.hasResults && this.selectedFileId !== null && !this.loading;
  }

  private validate(): boolean {
    this.validationMessage = null;
    if (!this.from) {
      this.validationMessage = '開始日を正しく入力してください。';
      return false;
    }
    if (!this.to) {
      this.validationMessage = '終了日を正しく入力してください。';
      return false;
    }
    if (this.from > this.to) {
      this.validationMessage = '開始日は終了日以前の日付を指定してください。';
      return false;
    }
    return true;
  }

  private fetch(page: number): void {
    if (!this.validate()) {
      return;
    }
    this.loading = true;
    this.errorMessage = null;
    this.errorHint = null;
    this.api.listLogFiles(this.from, this.to, page, this.perPage).subscribe({
      next: (res) => {
        this.items = res.items;
        this.page = res.page;
        this.totalItems = res.totalItems;
        this.totalPages = res.totalPages;
        // 初期選択・ページ切り替え後の選択はともに表示中ページの先頭行。
        this.selectedFileId = res.items.length > 0 ? res.items[0].fileId : null;
        this.loading = false;
        this.persist();
      },
      error: (err: ApiError) => {
        this.items = [];
        this.totalItems = 0;
        this.totalPages = 0;
        this.selectedFileId = null;
        this.errorMessage = err.message;
        this.errorHint = err.hint;
        this.loading = false;
      },
    });
  }

  private persist(): void {
    this.state.save({
      from: this.from,
      to: this.to,
      items: this.items,
      page: this.page,
      perPage: this.perPage,
      totalItems: this.totalItems,
      totalPages: this.totalPages,
      selectedFileId: this.selectedFileId,
    });
  }
}
