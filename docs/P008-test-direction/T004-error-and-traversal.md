あなたはExecutor(実装担当)です。実施後は結果を記録し、停止条件に該当しない限り次のテストタスクへ進んでください。

# 【テストID】T004 — エラー系とパストラバーサル

## 【目的】

* 異常系が仕様どおりのステータス・エラーコードで返ること、および `fileId` 経由でログディレクトリ外へ到達できないことを確認する (REQ-N-007, REQ-F-018)。

## 【参照テスト計画】

* `docs/P006-test-plan.md` §3.1 (異常系), §4 (セキュリティ観点)

## 【対象モジュール】

* `routers/*` / `services/metrics_service.py` (`resolve_file_id`) / `errors.py` / 例外ハンドラ

## 【前提条件】全モジュールビルドが成功していること

* U005 の単体テストが合格していること。

## 【使用するテストデータ】

* 実データディレクトリ
* `tmp_path` 上に作成した、ディレクトリ外を指すシンボリックリンク (作成できない環境では当該ケースを NOT RUN とする)

## 【事前準備】

* `sadf` の有無を記録する。

## 【実行手順】

* 下表の各リクエストを実行し、ステータスとエラーコードを確認する。

## 【実行コマンド】

* `python -m pytest backend/tests/integration/test_t004_errors.py -q`

## 【期待結果】

| リクエスト | HTTP | `error.code` |
| --- | --- | --- |
| `GET /api/log-files` (`from` 欠落) | 400 | `INVALID_PARAMETER` |
| `from=2026-13-01` (不正な日付) | 400 | `INVALID_PARAMETER` |
| `from=2026-08-31&to=2026-08-01` | 400 | `INVALID_PARAMETER` |
| `page=0` | 400 | `INVALID_PARAMETER` |
| `perPage=101` | 400 | `INVALID_PARAMETER` |
| `perPage=0` | 400 | `INVALID_PARAMETER` |
| `GET /api/log-files/notbase64!!/metrics` | 404 | `FILE_NOT_FOUND` |
| `fileId` = base64url(`../../etc/passwd`) | 404 | `FILE_NOT_FOUND` |
| `fileId` = base64url(`/etc/passwd`) | 404 | `FILE_NOT_FOUND` |
| `fileId` = base64url(`README.md`) | 404 | `FILE_NOT_FOUND` |
| `fileId` = base64url(`sa99`) (存在しない) | 404 | `FILE_NOT_FOUND` |
| `fileId` = base64url(`sa1`) (命名規則外) | 404 | `FILE_NOT_FOUND` |
| ディレクトリ外を指すシンボリックリンク | 404 | `FILE_NOT_FOUND` |

* **`sadf` が無い環境**では、`sa` ファイルの `fileId` に対する `GET .../metrics` が **503 / `SADF_UNAVAILABLE`** を返し、同一日の `sar` が存在する場合は `error.hint` にそのファイル名 (例: `sar23`) が含まれること。
* すべてのエラー応答が `{"error": {"code", "message", "detail", "hint"}}` の形をとること。
* `message` が日本語であること (REQ-N-013)。
* 500 応答を意図的に発生させた場合、`detail` に元の例外メッセージが含まれないこと。

## 【合否判定基準】

* 上表と追加条件をすべて満たせば PASS。1 つでも満たさなければ FAIL。
* とくに**パストラバーサル系が 1 件でも 404 以外を返した場合は、重大な欠陥として記録する。**

## 【失敗時に記録する内容】

* リクエスト内容、期待ステータス・コード、実際のステータス・コード・本文。

## 【修正禁止事項】

* アプリケーションコードを修正しない。

## 【次タスクへ進む条件】

* 結果を記録したら T005 へ進む。

## 重要:

* アプリケーションコードを修正しないでください。
* テスト失敗時に、その場で修正して再テストしないでください。
* テスト失敗時は、失敗内容をテスト記録に残してください。
