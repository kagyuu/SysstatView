あなたはExecutor(実装担当)です。実施後は結果を記録し、停止条件に該当しない限り次のテストタスクへ進んでください。

# 【テストID】T006 — 構造化ログ

## 【目的】

* 標準出力に 1 行 1 JSON の構造化ログが出ること、リクエストと `sadf` 実行が記録されることを確認する (REQ-N-009)。

## 【参照テスト計画】

* `docs/P006-test-plan.md` §4 (運用・ログ観点)

## 【対象モジュール】

* `logging_setup.py` / リクエストログミドルウェア / `readers/sa_binary.py`

## 【前提条件】全モジュールビルドが成功していること

* U001-T5 の単体テストが合格していること。

## 【使用するテストデータ】

* 実データディレクトリ

## 【事前準備】

* 標準出力を捕捉できる状態にする (`capsys` または専用ハンドラ)。

## 【実行手順】

1. `GET /api/health`、`GET /api/log-files`、`GET /api/log-files/{sar23}/metrics`、存在しない `fileId` への `GET` を実行する。
2. 捕捉した標準出力の各行を JSON として解釈する。

## 【実行コマンド】

* `python -m pytest backend/tests/integration/test_t006_logging.py -q`

## 【期待結果】

* 出力された各行が**単独で JSON として解釈できる** (複数行にまたがるレコードが無い)。
* 各レコードが `ts` / `level` / `event` / `message` を持つ。
* リクエストログに `method` / `path` / `status` / `durationMs` が含まれる。
* 404 を返したリクエストについても、`status=404` のリクエストログが出る。
* `sadf` を起動する経路を通った場合、`event="sadf.exec"` のレコードに `argv` / `returncode` / `durationMs` が含まれる (`sadf` 不在の環境では起動自体が失敗するため、`event="reader.failed"` または `sadf.exec` のいずれかが記録されること)。
* 読み取り失敗時に `event="reader.failed"` が `fileName` と `reason` 付きで記録される。
* `print` による出力が混在しない。

## 【合否判定基準】

* 上記をすべて満たせば PASS。JSON として解釈できない行が 1 行でもあれば FAIL。

## 【失敗時に記録する内容】

* JSON として解釈できなかった行の内容。
* 欠落していたフィールド名。

## 【修正禁止事項】

* アプリケーションコードを修正しない。

## 【次タスクへ進む条件】

* 結果を記録したら、`docs/P008-test-direction.md` の全項目の状態を更新し、Executor Step を終える。

## 重要:

* アプリケーションコードを修正しないでください。
* テスト失敗時に、その場で修正して再テストしないでください。
* テスト失敗時は、失敗内容をテスト記録に残してください。
