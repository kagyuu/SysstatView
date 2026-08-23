import { TestBed } from '@angular/core/testing';

import { LogFileInfo } from '../models/api.models';
import { SearchStateService } from './search-state.service';

const ITEM: LogFileInfo = {
  fileId: 'a', fileName: 'sar23', kind: 'sar', date: '2026-08-23', sizeBytes: 1, hostname: 'h',
};

describe('SearchStateService', () => {
  let svc: SearchStateService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    svc = TestBed.inject(SearchStateService);
  });

  it('未保存なら hasState は false', () => {
    expect(svc.hasState()).toBeFalse();
    expect(svc.restore()).toBeNull();
  });

  it('保存した状態がそのまま復元される', () => {
    svc.save({
      from: '2026-08-01', to: '2026-08-31', items: [ITEM], page: 2, perPage: 10,
      totalItems: 18, totalPages: 2, selectedFileId: 'a',
    });
    const s = svc.restore()!;
    expect(s.from).toBe('2026-08-01');
    expect(s.page).toBe(2);
    expect(s.selectedFileId).toBe('a');
    expect(s.items.length).toBe(1);
  });

  it('復元後に配列を書き換えても保持内容が変わらない', () => {
    svc.save({
      from: '2026-08-01', to: '2026-08-31', items: [ITEM], page: 1, perPage: 10,
      totalItems: 1, totalPages: 1, selectedFileId: 'a',
    });
    const first = svc.restore()!;
    first.items.push({ ...ITEM, fileId: 'b' });
    expect(svc.restore()!.items.length).toBe(1);
  });
});
