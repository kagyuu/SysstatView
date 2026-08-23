# SysstatView — プロジェクト全体の目次

sysstat が出力する日次ログ (`saDD` バイナリ / `sarDD` テキスト) を読み、時系列の性能データをブラウザでグラフ表示するビューア。

**まず読むもの**: 使い方は [`docs/P302-deliver.md`](./docs/P302-deliver.md)、技術的な全体像は [`docs/ArchitectureHandbook.md`](./docs/ArchitectureHandbook.md)。

## ソースツリー

| パス | 概要 |
| --- | --- |
| [`backend/INDEX.md`](./backend/INDEX.md) | FastAPI バックエンド。ログの読み取り・正規化・API |
| [`frontend/INDEX.md`](./frontend/INDEX.md) | Angular 20 の SPA。SC-01 (検索・選択) と SC-02 (グラフ表示) |

## 配布・実行

| パス | 概要 |
| --- | --- |
| `compose.yaml` | `web` (nginx) + `api` (FastAPI + sysstat) の 2 コンテナ構成 |
| `.env.example` | ログディレクトリと公開ポートの設定例 |
| `sysstat-log/var/log/sysstat/` | 同梱のテストデータ (`sa16`〜`sa24`、`sar15`〜`sar23`) |
| `require.txt` | 利用者から提示された元の要求 |

## ドキュメント

### 要求と設計

| パス | 概要 |
| --- | --- |
| [`docs/P001-requirement.md`](./docs/P001-requirement.md) | システム要件定義書。画面・API・非機能要件・要求 ID 一覧 |
| [`docs/P002-frontend-spec.md`](./docs/P002-frontend-spec.md) | ユーザインタフェース設計書。画面仕様と API の外部契約 |
| [`docs/P003-backend-spec.md`](./docs/P003-backend-spec.md) | システム詳細設計書。内部実現・解析アルゴリズム・不変条件 |
| [`docs/ADR.md`](./docs/ADR.md) | 設計判断とその理由 (ADR-001〜008) |
| [`docs/ArchitectureHandbook.md`](./docs/ArchitectureHandbook.md) | 技術的な全体像と**既知の制約・技術的負債** |

### 検証

| パス | 概要 |
| --- | --- |
| [`docs/P004-traceability-matrix.md`](./docs/P004-traceability-matrix.md) | 要求 45 件と設計の対応表、過剰実装の記録 |
| [`docs/P010-design-review.md`](./docs/P010-design-review.md) | 設計書横断レビュー (2 回実施、矛盾 3 件を是正) |
| [`docs/P011-impact-analysis.md`](./docs/P011-impact-analysis.md) | 矛盾点の影響分析 |
| [`docs/P201-review-report.md`](./docs/P201-review-report.md) | 実装横断レビュー結果と**未実行テストの明示** |

### 計画

| パス | 概要 |
| --- | --- |
| [`docs/P005-impl-plan.md`](./docs/P005-impl-plan.md) | 実装計画。8 スプリントの構成と実行環境の制約 |
| [`docs/P006-test-plan.md`](./docs/P006-test-plan.md) | テスト計画。テストレベル・重点観点・データのライフサイクル |
| [`docs/P101-impl-context.md`](./docs/P101-impl-context.md) | 実装担当向けの要約 (実装前に把握すべき 5 点) |

### 実装・テストの指示書

| パス | 概要 |
| --- | --- |
| [`docs/P007-impl-direction.md`](./docs/P007-impl-direction.md) | プログラム実装定義の目次 (U001〜U008)。子は `docs/P007-impl-direction/` |
| [`docs/P008-test-direction.md`](./docs/P008-test-direction.md) | 結合テスト定義の目次 (T001〜T006)。子は `docs/P008-test-direction/` |
| [`docs/P009-acceptance-direction.md`](./docs/P009-acceptance-direction.md) | 受け入れ結合テスト定義の目次 (A001〜A005)。子は `docs/P009-acceptance-direction/` |

### 記録

| パス | 概要 |
| --- | --- |
| [`docs/test-records/`](./docs/test-records/) | テスト実行記録 (合否と**実行できなかったテストの理由**) |
| [`docs/P302-deliver.md`](./docs/P302-deliver.md) | **配布物まとめと起動手順。起動直後に必ず行う確認を含む** |
