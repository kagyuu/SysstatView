あなたはReviewer Loop(実装横断レビュー担当)です。実施後は結果を記録し、停止条件に該当しない限り次のテストタスクへ進んでください。

# 【テストID】A005 — コンテナ構成

## 【目的】

* docker compose による配備が成立し、読み取り専用マウント・自動再起動・`sadf` の同梱が意図どおりであることを確認する (REQ-N-006 / REQ-N-010 / REQ-N-011)。

## 【参照テスト計画】

* `docs/P006-test-plan.md` §4 (可用性・セキュリティ), §6.3 (Docker が無い環境での扱い)

## 【対象モジュール】

* `compose.yaml` / `backend/Dockerfile` / `frontend/Dockerfile` / `frontend/nginx.conf`

## 【前提条件】全モジュールビルドが成功していること

* U008 が完了していること。
* **Docker と docker compose が利用可能であること。** 利用できない場合は本テストを実行できない。

## 【使用するテストデータ】

* 実データディレクトリ (ホスト側からマウントする)

## 【事前準備】

* `docker --version` と `docker compose version` を確認する。
* **利用できない場合は、本テスト全体を NOT RUN として記録し、その理由 (「この環境に Docker が無いため」) を明記する。PASS として扱わない。**
* 実行できる範囲の代替確認として、`compose.yaml` が YAML として妥当であることだけは確認する。

## 【実行手順】

1. `docker compose build` を実行する。
2. `docker compose up -d` を実行する。
3. `http://localhost:8080/` が SC-01 を返すことを確認する。
4. `http://localhost:8080/api/health` を確認する。
5. `api` コンテナ内で `sadf -V` を実行する。
6. `sa` ファイルを選択してグラフが表示されることを確認する。
7. `api` コンテナ内からマウント先へ書き込みを試みる。
8. `api` コンテナのプロセスを強制終了し、自動再起動を確認する。
9. `docker compose logs api` でログを確認する。

## 【実行コマンド】

* `docker compose build && docker compose up -d`
* `curl -s http://localhost:8080/api/health`
* `docker compose exec api sadf -V`
* `docker compose exec api sh -c 'touch /var/log/sysstat/_w 2>&1 || echo READONLY_OK'`
* `docker compose logs api --tail 50`

## 【期待結果】

* 手順1: ビルドが成功する。
* 手順3: SC-01 の HTML が返る (nginx の SPA 配信が動作)。
* 手順4: HTTP 200、`status="ok"`、**`sadfAvailable=true`**、`sadfVersion` が非 null (REQ-N-011)。`readableFileCount=18` (`sa` も読める)。
* 手順5: `sadf` のバージョンが表示される。
* 手順6: **`sa` ファイルのグラフが表示される。** これはこの環境でのみ確認できる、`sa` 経路の唯一の実地検証である。
* 手順7: 書き込みが**拒否される** (`READONLY_OK` が出る) (REQ-N-006)。
* 手順8: コンテナが自動的に再起動する (REQ-N-010)。
* 手順9: 1 行 1 JSON の構造化ログが出力されている (REQ-N-009)。

## 【合否判定基準】

* 上記をすべて満たせば PASS。
* Docker が無く実行できない場合は **NOT RUN**。**PASS として扱わない。**
* 手順4・手順6 が失敗した場合、`docs/P003-backend-spec.md` §9.2・§9.3 の ★FIXME★ (`sadf -j` のフィールド名が未確認) が原因である可能性が高い。実際の `sadf -j -- -A` の出力を取得して記録する。

## 【失敗時に記録する内容】

* 失敗した手順とコマンド出力全文。
* 手順6 が失敗した場合は、`docker compose exec api sadf -j -- -A /var/log/sysstat/sa23 | head -100` の出力を記録する。これが `docs/P003-backend-spec.md` §9.2 を修正するための一次情報になる。

## 【修正禁止事項】

* アプリケーションコードを修正しない。
* Dockerfile / compose.yaml を修正しない。

## 【次タスクへ進む条件】

* 結果を記録したら、`docs/P009-acceptance-direction.md` の全項目の状態を更新し、Reviewer Loop の判定へ進む。

## 重要:

* アプリケーションコードを修正しないでください。
* テスト失敗時に、その場で修正して再テストしないでください。
* テスト失敗時は、失敗内容をテスト記録に残してください。
