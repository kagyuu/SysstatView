あなたはExecutor(実装担当)です。実施後は結果を記録し、停止条件に該当しない限り次のテストタスクへ進んでください。

# 【テストID】T003 — カタログAPIの結合

## 【目的】

* ディレクトリ走査 → 採取日解決 → 期間フィルタ → ソート → ページングが連携して `GET /api/log-files` の仕様どおりに動くことを確認する。

## 【参照テスト計画】

* `docs/P006-test-plan.md` §3.1 (log-files エンドポイント)

## 【対象モジュール】

* `routers/log_files.py` → `services/catalog_service.py` → `readers/sar_text.py` (`read_header`) / `readers/sa_binary.py` (`sadf -H`)

## 【前提条件】全モジュールビルドが成功していること

* U004 の単体テストが合格していること。

## 【使用するテストデータ】

* 実データ 18 件 (`sa16`〜`sa24`、`sar15`〜`sar23`)
* ページ境界の検証用に、`tmp_path` へコピーして件数を調整したディレクトリ

## 【事前準備】

* `sadf` の有無を記録する。**`sadf` が無い環境では `sa` 9 件が unreadable となり、一覧は `sar` 9 件のみになる。この条件で期待値を立てる。**
* 実データを書き換えない。件数調整は `tmp_path` 上のコピーで行う。

## 【実行手順】

1. 実データディレクトリに対して各種パラメータで `GET /api/log-files` を実行する。
2. `tmp_path` にコピーしたディレクトリでページ境界を検証する。

## 【実行コマンド】

* `python -m pytest backend/tests/integration/test_t003_catalog_api.py -q`

## 【期待結果】

* **`sadf` 有りの環境**: `from=2026-08-01&to=2026-08-31&perPage=100` で `totalItems=18`。並び順が日付昇順 → 同一日は `sa` → `sar`。
* **`sadf` 無しの環境**: 同条件で `totalItems=9` (`sar15`〜`sar23` のみ)。`sa` が 1 件も含まれない。
* 境界: `from=2026-08-23&to=2026-08-23` で `sar23` (と `sadf` 有りなら `sa23`) のみが返る。
* ページング: `perPage=10` で `totalPages` が正しく、2 ページ目の件数が `totalItems - 10` と一致する。
* 0 件: `from=2020-01-01&to=2020-01-02` で `totalItems=0`, `totalPages=0`, `items` が空配列。
* 超過ページ: `page=99` で HTTP 200 かつ `items` が空配列。
* 各 `items[]` が `fileId` / `fileName` / `kind` / `date` / `sizeBytes` / `hostname` を持ち、フィールド名が camelCase である。
* `GET /api/health` の `readableFileCount` が一覧の総件数 (期間を全体に広げたとき) と整合する。

## 【合否判定基準】

* 上記をすべて満たせば PASS。1 つでも満たさなければ FAIL。

## 【失敗時に記録する内容】

* 実行したパラメータ、期待値、実際の値。`sadf` の有無も記録する (期待値が変わるため)。

## 【修正禁止事項】

* アプリケーションコードを修正しない。

## 【次タスクへ進む条件】

* 結果を記録したら T004 へ進む。

## 重要:

* アプリケーションコードを修正しないでください。
* テスト失敗時に、その場で修正して再テストしないでください。
* テスト失敗時は、失敗内容をテスト記録に残してください。
