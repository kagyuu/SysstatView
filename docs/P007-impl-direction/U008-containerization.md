あなたはExecutor(実装担当)です。実施後は完了条件を確認し、停止条件に該当しない限り自動的に次のタスクへ進んでください。

# 【スプリントID】U008 — containerization

**注意**: この開発環境には Docker が無い (`docs/P005-impl-plan.md` §5)。本スプリントの成果物は**作成できるがビルド・起動の確認ができない**。完了条件を「実際に起動した」と記載してはならない。確認できたこと・できなかったことを区別して記録すること。

## タスク一覧(OKF副目次)

- [x] U008-T1 [バックエンドのDockerfile](#u008-t1-バックエンドのdockerfile) — sysstat 同梱
- [x] U008-T2 [フロントエンドのDockerfileとnginx](#u008-t2-フロントエンドのdockerfileとnginx) — ビルドと配信・プロキシ
- [x] U008-T3 [compose定義](#u008-t3-compose定義) — 2 サービス・読み取り専用マウント
- [x] U008-T4 [構成の静的検証](#u008-t4-構成の静的検証) — 実行できない範囲の明示

---

## U008-T1: バックエンドのDockerfile

### 【目的】

* `sadf` を含むバックエンドイメージを定義する (REQ-N-011)。

### 【作成・編集対象ファイル】

* `backend/Dockerfile`, `backend/.dockerignore`

### 【参照すべき仕様箇所】

* `docs/P005-impl-plan.md` §3 U008 (インフラ構成の決定内容の表)

### 【実装内容】

* ベース: `python:3.12-slim`。
* `apt-get update && apt-get install -y --no-install-recommends sysstat && rm -rf /var/lib/apt/lists/*` で **sysstat を導入する**。
* `requirements.txt` を先にコピーして `pip install` し、その後アプリコードをコピーする (レイヤキャッシュのため)。
* 非 root ユーザーで実行する。
* `CMD` は Uvicorn を **`--workers 2`** で起動する (`docs/P005-impl-plan.md` の決定)。
* `EXPOSE 8000`。
* `.dockerignore` に `tests/`, `__pycache__/`, `.pytest_cache/` を含める。

### 【実装してはいけないこと】

* ログディレクトリをイメージに焼き込むこと (実行時にマウントする)。

### 【Unit Test内容】

* なし (Dockerfile はビルドできないため単体テスト対象外)。

### 【実行コマンド】

* なし。**Docker が無いためビルド確認を行えない。**

### 【完了条件】

* Dockerfile が作成され、記述内容が仕様と一致することをレビューで確認する。
* **「ビルド確認済み」と記録しない。**

### 【次タスクに進む前の停止条件】

* なし。

---

## U008-T2: フロントエンドのDockerfileとnginx

### 【目的】

* Angular をビルドして nginx で配信し、`/api/*` を API へ転送する (P003 §2 の同一オリジン方針)。

### 【作成・編集対象ファイル】

* `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/.dockerignore`

### 【実装内容】

* マルチステージ: `node:22-alpine` でビルド → `nginx:alpine` へ成果物をコピー。
* `nginx.conf`:
  * 静的ファイルの配信ルート。
  * `location /api/ { proxy_pass http://api:8000; }` — **末尾スラッシュの有無でパスの書き換わり方が変わる。`/api/` プレフィックスを保ったまま転送すること。**
  * SPA フォールバック: `try_files $uri $uri/ /index.html;`
  * メトリクス応答が大きくなるためプロキシのバッファとタイムアウトを緩める。
* `EXPOSE 80`。

### 【実装してはいけないこと】

* CORS ヘッダの追加 (同一オリジンのため不要)。

### 【Unit Test内容】

* なし。

### 【実行コマンド】

* なし。**Docker が無いため確認を行えない。**

### 【完了条件】

* ファイルが作成され、記述内容が仕様と一致することをレビューで確認する。

### 【次タスクに進む前の停止条件】

* なし。

---

## U008-T3: compose定義

### 【目的】

* 2 サービス構成を定義する (REQ-N-006, REQ-N-010)。

### 【作成・編集対象ファイル】

* `compose.yaml`, `.env.example`

### 【実装内容】

* サービス `api`: `backend/` をビルド。`SYSSTAT_LOG_DIR=/var/log/sysstat`。**ホストのポートを公開しない。**
* サービス `web`: `frontend/` をビルド。`ports: ["8080:80"]`。`depends_on: [api]`。
* 両サービスに `restart: unless-stopped`。
* `api` の volumes: `${SYSSTAT_LOG_HOST_DIR:-./sysstat-log/var/log/sysstat}:/var/log/sysstat:ro` — **`:ro` を必ず付ける** (REQ-N-006)。
* `.env.example` に `SYSSTAT_LOG_HOST_DIR` の説明を書く。

### 【Unit Test内容】

* なし。

### 【実行コマンド】

* なし。**Docker が無いため `docker compose config` による検証も行えない。**

### 【完了条件】

* ファイルが作成され、記述内容が仕様と一致することをレビューで確認する。

### 【次タスクに進む前の停止条件】

* なし。

---

## U008-T4: 構成の静的検証

### 【目的】

* 実行できない範囲を明示し、後続フェーズと利用者に引き継ぐ。

### 【作成・編集対象ファイル】

* `docs/ArchitectureHandbook.md` の「既知の制約・技術的負債」への追記 (P022 実行後に行う。P022 未実行の場合は本タスクで作成される内容をメモとして残し、P022 が取り込む)

### 【実装内容】

* YAML / Dockerfile の構文を、Docker を使わずに検証できる範囲で確認する (YAML パーサでの読み込み確認など)。
* 次を明記する。
  * `compose.yaml` が YAML として妥当であること (確認できる)。
  * イメージのビルド、コンテナの起動、nginx のプロキシ動作、`sadf` の実行可否は **この環境では未確認**であること。
  * 利用者が最初に行うべき確認手順 (`docker compose up -d` → `GET /api/health` で `sadfAvailable` が `true` であること) を P302 に記載する必要があること。

### 【Unit Test内容】

* `compose.yaml` が YAML として読み込めること (Python の `yaml` で確認)。

### 【実行コマンド】

* `python -c "import yaml,sys; yaml.safe_load(open('compose.yaml')); print('compose.yaml: valid YAML')"`

### 【完了条件】

* 上記が成功する。
* 未確認事項が記録されている。
* `docs/P007-impl-direction.md` の U008 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* なし。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
* **確認できなかったことを、確認できたかのように記録しないでください。**
