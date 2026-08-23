# P302 納品物まとめ・配布手順 — SysstatView

* 作成フェーズ: P302 (Closing)
* リリース判定: **条件付き可** (§10 の未整備事項を確認したうえで運用に入ること)

---

## 1. アプリケーション概要

Linux の性能統計収集ツール **sysstat** が `/var/log/sysstat/` に日次で出力するログを読み、時系列の性能データをブラウザでグラフ表示するビューアです。

* 画面は 2 つだけです。**ログファイルを選ぶ → グラフを見る → 戻る。**
* 対象ファイルは 2 種類あり、どちらも一覧に並びます。
  * `sarDD` (テキスト) — アプリが直接解析します。
  * `saDD` (バイナリ) — コンテナ内の `sadf` コマンドで変換してから解析します。
* 認証はありません。**社内ネットワーク内での利用を前提としています。**

## 2. アプリケーション種別

**サービス提供型システム** (フロントエンド + バックエンドの 2 コンテナ構成)。Docker Compose で配布します。

## 3. 納品物一覧

| 区分 | パス | 内容 |
| --- | --- | --- |
| 起動定義 | `compose.yaml` | `web` (nginx) + `api` (FastAPI + sysstat) の 2 サービス |
| 設定例 | `.env.example` | ログディレクトリと公開ポート |
| バックエンド | `backend/` | FastAPI アプリ、Dockerfile、テスト |
| フロントエンド | `frontend/` | Angular 20 の SPA、nginx 設定、Dockerfile |
| テストデータ | `sysstat-log/var/log/sysstat/` | `sa16`〜`sa24`、`sar15`〜`sar23` |
| 目次 | `INDEX.md` | プロジェクト全体の入口 |
| 設計・記録 | `docs/` | 要件・設計・テスト計画・ADR・テスト記録 |

## 4. 起動方法

### 4.1 前提

* Docker および Docker Compose が利用できること。
* 閲覧したい sysstat のログファイル (`saDD` / `sarDD`) が 1 つのディレクトリ直下にあること。

### 4.2 手順

```bash
# 1. 設定ファイルを用意する
cp .env.example .env

# 2. .env を編集し、閲覧したいログディレクトリを指定する
#    SYSSTAT_LOG_HOST_DIR=/var/log/sysstat        ← 実運用のログを見る場合
#    SYSSTAT_LOG_HOST_DIR=./sysstat-log/var/log/sysstat  ← 同梱のテストデータを見る場合 (既定)

# 3. 起動する
docker compose up -d --build

# 4. ブラウザで開く
#    http://localhost:8080/
```

### 4.3 停止・ログ確認

```bash
docker compose down          # 停止
docker compose logs -f api   # バックエンドのログ (1 行 1 JSON)
docker compose logs -f web   # nginx のログ
```

## 5. 起動直後に必ず行う確認 【重要】

**本アプリは `sadf` を導入できない環境で開発したため、`sa` (バイナリ) 経路を実地で検証できていません** (§10-1)。運用に入る前に、次を必ず確認してください。

### 手順 1: `sadf` が使えることを確認する

```bash
curl -s http://localhost:8080/api/health
```

期待する応答:

```json
{
  "status": "ok",
  "sadfAvailable": true,          ← ここが true であること
  "sadfVersion": "sysstat ...",   ← null でないこと
  "readableFileCount": 18,        ← sa と sar の両方が読めていること
  "unreadableFileCount": 0
}
```

* `sadfAvailable` が `false` の場合、`api` コンテナに sysstat が入っていません。イメージを再ビルドしてください。
* `unreadableFileCount` が 0 より大きい場合、そのファイル数だけ**採取日を読めず一覧に出ていません**。`docker compose logs api | grep reader.failed` で対象ファイルと理由を確認できます。

### 手順 2: `sa` ファイルのグラフが表示されることを確認する

1. ブラウザで `http://localhost:8080/` を開きます。
2. 期間を指定して検索し、一覧の **種別が `sa` の行**を選びます。
3. 「表示」を押してグラフが出ることを確認します。

**これが失敗した場合**、`sadf` の JSON 出力のフィールド名が本アプリの想定と異なる可能性が高いです (§10-1)。次のコマンドで出力を採取し、開発者に渡してください。

```bash
docker compose exec api sadf -j -- -A /var/log/sysstat/sa23 | head -100
```

修正が必要な箇所は `backend/app/metrics/catalog.py` の `SADF_KEY_TO_GROUP` / `SADF_FIELD_TO_METRIC` の 2 つの対応表に限定される設計になっています。

### 手順 3: `sar` ファイルのグラフが表示されることを確認する

種別が `sar` の行を選んでグラフが出ることを確認します。**こちらは実データで検証済み**です。

## 6. 使い方

### 画面 1: ログファイル検索・選択

* 上段で**開始日・終了日**を指定して「検索」を押します。初期値は**今月の 1 日から末日**です。
* 下段に該当するログファイルが**1 ページ 10 件**で並びます。ラジオボタンで 1 件選び、「表示」を押します。
* 一覧には**採取日**が表示されます。ファイル名 (`sa23` など) は日 (DD) しか持たず月をまたぐと循環するため、ファイル内部から読み取った採取日を基準にしています。
* 同じ日について `sa` と `sar` の両方があれば、**両方が別の行として並びます**。どちらを読むかは選べます。

### 画面 2: グラフ表示

* 選んだファイルに含まれる時系列データが**すべて**グラフになります (最大 21 メトリクスグループ、約 30 グラフ)。
* 各グラフの**前に**、何を表しているかの見出しと、指標の意味の説明が出ます。
* 「戻る」を押すと画面 1 に戻ります。**検索条件・ページ番号・選択していた行が、遷移前のまま復元されます。**

## 7. 外部公開する場合

**本構成は TLS 終端を行いません。** 社内ネットワーク内での利用を前提としています (ADR-008)。

社内ネットワーク外へ公開する場合は、`web` サービスの前段にリバースプロキシ (nginx / Caddy / ALB など) を置き、そこで TLS 終端とアクセス制御を行ってください。**認証機能はアプリに実装されていません。**

## 8. 開発者向け

```bash
# バックエンド
cd backend
pip install -r requirements-dev.txt
SYSSTAT_LOG_DIR=../sysstat-log/var/log/sysstat python -m uvicorn app.main:app --port 8000
python -m pytest tests -q                    # テスト (210 passed / 11 skipped)

# フロントエンド
cd frontend
npm install
npm start        # http://localhost:4200 (/api は localhost:8000 へ転送)
npm test         # テスト (37 SUCCESS)
npm run build
```

## 9. 仕様・テスト・テスト実装の対応表

| 仕様ID | 要求ID | 仕様内容 | 対応するテスト計画 | 対応するテスト指示 | 対応するテスト実装/実行コマンド | 最新結果 | 証跡 | 状態 | 出荷影響 |
|---|---|---|---|---|---|---|---|---|---|
| SPEC-SCREEN-001 | REQ-F-003〜010, 020, 021, 025 | SC-01 検索・一覧・ページング・単一選択・遷移 | docs/P006-test-plan.md §3.3 | docs/P009-acceptance-direction/A001-end-to-end-navigation.md | `npm --prefix frontend test` | PASS | docs/test-records/20260824-0750-test-record.md A001 | OK | - |
| SPEC-SCREEN-002 | REQ-F-011〜013 | SC-02 グラフ表示・見出しと説明 | docs/P006-test-plan.md §3.3 | A001 | `npm --prefix frontend test` | PASS | 同上 | OK | - |
| SPEC-SCREEN-003 | REQ-F-014 | 戻り時の状態復元 | docs/P006-test-plan.md §2 観点C | A001 | `npm --prefix frontend test` | PASS | 同上 | OK | 実ブラウザでの通し操作は未実施 (E2E ハーネス無し) |
| SPEC-API-001 | REQ-N-015 | `GET /api/health` | docs/P006-test-plan.md §3.1 | docs/P009-acceptance-direction/A002-sar-only-operation.md | `python -m pytest backend/tests/acceptance/test_a002_sar_only.py -q` | PASS | 同記録 A002 | OK | - |
| SPEC-API-002 | REQ-F-002, 005, 015, 017, 026 | `GET /api/log-files` | docs/P006-test-plan.md §3.1 | docs/P008-test-direction/T003-catalog-api.md | `python -m pytest backend/tests/integration/test_t003_catalog_api.py -q` | PASS | 同記録 T003 | OK | - |
| SPEC-API-003 | REQ-F-001, 012, 016, 019, 022, 023 | `GET /api/log-files/{fileId}/metrics` | docs/P006-test-plan.md §3.1 | docs/P008-test-direction/T001-sar-pipeline.md | `python -m pytest backend/tests/integration/test_t001_sar_pipeline.py -q` | PASS | 同記録 T001 | OK | `sar` 経路のみ実データ検証。`sa` 経路は未検証 |
| SPEC-API-004 | REQ-F-013 | `GET /api/metric-catalog` | docs/P006-test-plan.md §3.1 | T001 | `python -m pytest backend/tests/integration/test_t001_sar_pipeline.py -q` | PASS | 同記録 T001 | OK | - |
| SPEC-PARSE-001 | REQ-F-027, 028, 029 | `sar` テキスト解析 (繰り返しヘッダ・`Average:`・1 行目の日付) | docs/P006-test-plan.md §2 観点B | T001 | `python -m pytest backend/tests/test_sar_text.py backend/tests/test_sar_realdata.py -q` | PASS | 同記録 T001 | OK | - |
| SPEC-PARSE-002 | REQ-F-024 | `sa` / `sar` 両経路の結果一致 | docs/P006-test-plan.md §2 観点A | docs/P008-test-direction/T002-dual-path-equivalence.md | `python -m pytest backend/tests/integration/test_t002_dual_path.py -q` | **NOT RUN** | 同記録 T002 | **BLOCKED** | **`sadf` が無く実行できない。§5 手順 2 で運用側が確認すること** |
| SPEC-ERR-001 | REQ-F-018, 020, 021 | エラー応答の形式とコード | docs/P006-test-plan.md §3.1 | docs/P008-test-direction/T004-error-and-traversal.md | `python -m pytest backend/tests/integration/test_t004_errors.py -q` | PASS | 同記録 T004 | OK | - |
| SPEC-NFR-001 | REQ-N-001, 002, 013 | Angular + FastAPI、日本語表示 | docs/P006-test-plan.md | 全テスト | `npm test` / `pytest` | PASS | 同記録 | OK | Angular は 18 系ではなく **20 系** (ADR-005) |
| SPEC-NFR-002 | REQ-N-003, 004 | API の応答時間 | docs/P006-test-plan.md §4 | docs/P009-acceptance-direction/A004-performance.md | `python -m pytest backend/tests/acceptance/test_a004_performance.py -q -s` | PASS | 同記録 A004 | OK | 実測 P95 は基準の 1/10 以下 |
| SPEC-NFR-003 | REQ-N-005 | SC-02 の初回グラフ描画 3 秒以内 | docs/P006-test-plan.md §4 | A004 項目 4 | - | **NOT RUN** | 同記録 A004 | **BLOCKED** | ブラウザ計測手段が無い。§10-3 |
| SPEC-NFR-004 | REQ-N-007, 008 | パストラバーサル防止・シェル不使用 | docs/P006-test-plan.md §4 | T004 | `python -m pytest backend/tests/integration/test_t004_errors.py backend/tests/test_fileid.py -q` | PASS | 同記録 T004 | OK | シンボリックリンクのケースのみ Windows で未実行 |
| SPEC-NFR-005 | REQ-N-009 | 標準出力への構造化ログ | docs/P006-test-plan.md §4 | docs/P008-test-direction/T006-structured-log.md | `python -m pytest backend/tests/integration/test_t006_logging.py -q` | PASS | 同記録 T006 | OK | - |
| SPEC-NFR-006 | REQ-N-014 | スイート 2 回実行の同一性 | docs/P006-test-plan.md §5.5 | - | `pytest tests -q` を 2 回 / `npm test` を 2 回 | PASS | 同記録 集計 | OK | - |
| SPEC-NFR-007 | REQ-N-016 | 一覧でのキャッシュ | docs/P006-test-plan.md §4 | docs/P008-test-direction/T005-cache-effect.md | `python -m pytest backend/tests/integration/test_t005_cache.py -q` | PASS | 同記録 T005 | OK | - |
| SPEC-NFR-008 | REQ-N-010, 012 | 再起動耐性・複数ワーカー | docs/P006-test-plan.md §4.1 | docs/P009-acceptance-direction/A003-restart-resilience.md | `python -m pytest backend/tests/acceptance/test_a003_restart.py -q` | PASS | 同記録 A003 | OK | ローカルプロセスでの 3 回起動で確認。コンテナ再起動は未確認 |
| SPEC-NFR-009-CONTAINER | REQ-N-006, 011 | 読み取り専用マウント・sysstat 同梱 | docs/P006-test-plan.md §6.3 | docs/P009-acceptance-direction/A005-container-deployment.md | `docker compose build && docker compose up -d` | **NOT RUN** | 同記録 A005 | **BLOCKED** | **Docker が無く実行できない。§5 で運用側が確認すること** |
| SPEC-FLOW-001 | - | 配布トポロジー (同一オリジンでの `/api` 相対パス) の疎通。画面・API 単位の要求に紐づかないため要求 ID は `-` | docs/P006-test-plan.md §6.3 | - (P302 実行前チェック項目 7) | `python backend/tests/acceptance/_topology_probe.py` | PASS | 同記録 TOPO-01 | OK | nginx 相当の経路構成を再現して確認。nginx 実体は未検証 |

**網羅性の確認**: `docs/P004-traceability-matrix.md` の要求 ID 45 件 (REQ-F-001〜029、REQ-N-001〜016) は、上表のいずれかの行に現れています。落としているものはありません。

## 10. 未整備事項・人間による確認事項

### 10-1. `sa` (バイナリ) 経路が実地で未検証 【最重要】

* **状況**: 開発環境に `sadf` を導入できず (Windows に sysstat が無く、WSL の `sudo` がパスワードを要求するため非対話でインストール不可)、`sadf -j -- -A` の**実出力を一度も確認していません**。
* **影響**: `backend/app/metrics/catalog.py` の `SADF_KEY_TO_GROUP` / `SADF_FIELD_TO_METRIC` は sysstat の公開仕様にもとづく記述であり、実際のフィールド名と異なる可能性があります。その場合、`sa` ファイルのグラフが出ない、または一部のグラフが欠けます。
* **検証済みの範囲**: `sadf` 呼び出しのモックとフィクスチャによる単体テスト 17 件は合格しています。**「実 `sadf` で動作確認した」とは記載していません。**
* **確認方法**: §5 の手順 1・2。
* **CR 起票候補**: 実出力との相違が判明した場合。

### 10-2. コンテナ構成が未検証 (A005)

* **状況**: 開発環境に Docker が無く、`docker compose build` / `up` を実行していません。
* **確認できた範囲**: `compose.yaml` が YAML として妥当であること、`api` の volumes が `:ro` で終わること、`api` がホストにポートを公開していないこと。
* **未確認**: イメージのビルド、コンテナ起動、nginx のプロキシ動作、読み取り専用マウントの実効性、自動再起動。
* **補足**: nginx と等価な経路構成を Python で再現した疎通確認 (TOPO-01) は PASS しています。ただし**nginx 自体の挙動は未検証**です。`nginx.conf` の `proxy_pass http://api:8000;` に末尾スラッシュを付けると全 API が 404 になるため、編集時は注意してください。
* **確認方法**: §4 で起動し、§5 を実施する。

### 10-3. SC-02 の初回グラフ描画時間 (REQ-N-005) が未測定

* **状況**: ブラウザ描画時間の計測手段が無いため測定していません。**合格に数えていません。**
* **確認方法**: 実ブラウザで `sar23` (ネットワークインタフェース 22 本、約 30 グラフ) を開き、最初のグラフが 3 秒以内に描画されることを確認してください。

### 10-4. 実ブラウザでの通し操作 (E2E) が未実施

* **状況**: E2E ハーネス (Playwright など) を導入していません。状態復元 (REQ-F-014) は、`SearchStateService` を共有するコンポーネントテストで検証しました。
* **確認方法**: §6 の手順で、2 ページ目の任意の行を選んで表示 → 戻る、を実際に操作し、ページ番号と選択行が戻ることを確認してください。

### 10-5. 要求書に対応の無い仕様が 4 件あります (過剰実装)

`docs/P004-traceability-matrix.md` §4 に記録済みです。いずれも要求を詳細化する過程で必要性が判明したもので、要求に反する機能追加ではありません。**要求書側への追記が妥当と判断していますが、人間の確認が必要です** ★FIXME★

1. `GET /api/health` の `readableFileCount` / `unreadableFileCount`
2. SC-02 のホスト情報表示 (ホスト名・カーネル・アーキテクチャ・CPU 数)
3. 単位ごとのグラフ分割 (1 グループが複数グラフになる)
4. `GET /api/log-files` の `perPage` パラメータ

### 10-6. 実装中に発見し、要求書を拡張した事項

* **メトリクスグループが 18 ではなく 21 でした。** 実データに PSI (Pressure Stall Information) の 3 グループ (`%scpu-*` / `%sio-*` / `%smem-*`) が含まれており、`docs/P001-requirement.md` §7 の当初の調査で取りこぼしていました。REQ-F-012「格納されている時系列データが全てグラフ表示される」を満たすため実装に追加し、関連文書を更新しています。

### 10-7. 設計時の想定から変更した技術選定

| 項目 | 当初 | 実際 | 理由 |
| --- | --- | --- | --- |
| Angular | 18 系 | **20 系** | 開発環境の Node v24.12.0 を Angular 18 がサポートしない (Angular 22 は Node 24.15+ を要求し、これも満たせない) |
| グラフ描画 | Chart.js + `ng2-charts` | **Chart.js を直接利用** | `ng2-charts@10` が Angular 22 以上を要求し、Angular 20 と両立しない |

いずれも `docs/ADR.md` ADR-005 に理由とともに記録済みです。

### 10-8. その他の既知の制約

`docs/ArchitectureHandbook.md` §9 に 7 件記載しています。とくに次の 2 点は運用上の留意事項です。

* **開発環境 (Python 3.14) と実行環境 (コンテナの Python 3.12) のバージョンが異なります。** 3.13 以降の構文を使わない規約で実装していますが、この環境のテストでは検出できない種類のリスクです。
* **`sar` テキストのロケール差異 (AM/PM 表記) と日をまたぐファイルは、実データで検証できていません。** どちらも対応コードとテストは書いてありますが、合成データによる検証にとどまります。

## 11. リリース判定

**条件付き可。**

* `sar` (テキスト) 経路については、実データ 9 ファイルで完全に検証済みであり、そのまま利用できます。
* `sa` (バイナリ) 経路は**実地未検証**です。§5 の手順 1・2 を実施し、問題がないことを確認してから運用に入ってください。
* コンテナ構成も未検証のため、初回起動時に §5 の確認を必ず行ってください。
