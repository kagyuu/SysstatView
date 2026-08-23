# P008 結合テスト定義 兼 結合テスト指示書 — 目次 (OKF形式)

* 作成フェーズ: P008 (Plan Loop Step)
* 対象: スプリント内 / モジュール間の結合テスト
* 上位文書: `docs/P006-test-plan.md` / `docs/P002-frontend-spec.md` / `docs/P003-backend-spec.md`

## 目次

- [x] T001 [sar経路の結合](./P008-test-direction/T001-sar-pipeline.md) — API→リーダ→正規化を実データで通す
- [~] T002 [2経路の一致](./P008-test-direction/T002-dual-path-equivalence.md) — 観点A。※NOT RUN: この環境に `sadf` が無く実行できない (合格として扱わない)
- [x] T003 [カタログAPIの結合](./P008-test-direction/T003-catalog-api.md) — 走査→採取日→期間→ページング
- [x] T004 [エラー系とパストラバーサル](./P008-test-direction/T004-error-and-traversal.md) — 異常系の一括検証
- [x] T005 [キャッシュ効果](./P008-test-direction/T005-cache-effect.md) — 再読み取りが起きないこと
- [x] T006 [構造化ログ](./P008-test-direction/T006-structured-log.md) — 標準出力への JSON ログ

## テストレベルの位置づけ

本フェーズは**スプリント内 / モジュール間**の結合を対象とする。スプリントをまたぐ通し操作・システムテスト・受け入れテストは `docs/P009-acceptance-direction.md` が担当する。

## 実行環境の前提と、実行できないテスト

`docs/P006-test-plan.md` §6.2 のとおり、この開発環境には `sadf` が無い。

| テストID | `sadf` 有りの環境 | `sadf` 無しの環境 (現環境) |
| --- | --- | --- |
| T001 | PASS 可能 | **PASS 可能** (`sar` のみを使うため) |
| T002 | PASS 可能 | **NOT RUN** (実行できない。合格として扱わない) |
| T003 | 18 件が readable | **`sar` 9 件のみ readable。この条件で判定する** |
| T004 | 全ケース実行可能 | **全ケース実行可能** (`sadf` 不在の 503 はむしろ確実に検証できる) |
| T005 | PASS 可能 | **PASS 可能** |
| T006 | PASS 可能 | **PASS 可能** |

* **NOT RUN を PASS として記録しない。**

## テストデータのライフサイクル

* `docs/P006-test-plan.md` §5 に従う。ベースラインは `sysstat-log/var/log/sysstat/` の内容そのもの。復元単位はスイート実行ごと。
* 書き込みを伴うケースは `tmp_path` にコピーして行い、実データを汚さない。
* テストスイートを 2 回続けて実行し、同じ結果になることを確認する (REQ-N-014)。
