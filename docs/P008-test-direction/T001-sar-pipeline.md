あなたはExecutor(実装担当)です。実施後は結果(PASS/FAIL/BLOCKED/NOT RUN)を記録し、停止条件に該当しない限り次のテストタスクへ進んでください。

# 【テストID】T001 — sar経路の結合

## 【目的】

* `GET /api/log-files/{fileId}/metrics` から `sar` テキストリーダ・正規化・メトリクス定義までが、**実データ**で連携して動くことを確認する。この環境で完全に検証できる中核経路である。

## 【参照テスト計画】

* `docs/P006-test-plan.md` §2 観点B, §3.1 (metrics エンドポイント), §7

## 【対象モジュール】

* `routers/log_files.py` → `services/metrics_service.py` → `readers/sar_text.py` → `readers/normalize.py` → `metrics/catalog.py`

## 【前提条件】対象スプリントの全モジュールビルドが成功していること

* U001〜U005 の単体テストがすべて合格していること。

## 【使用するテストデータ】

* `sysstat-log/var/log/sysstat/sar15`〜`sar23` (実データ 9 件)

## 【事前準備】

* `SYSSTAT_LOG_DIR` を実データディレクトリに向ける。
* 実データを書き換えない。

## 【実行手順】

1. `GET /api/log-files?from=2026-08-01&to=2026-08-31&perPage=100` で `sar` の `fileId` を取得する。
2. 取得した 9 件すべてについて `GET /api/log-files/{fileId}/metrics` を実行する。
3. 応答を検証する。

## 【実行コマンド】

* `python -m pytest backend/tests/integration/test_t001_sar_pipeline.py -q`

## 【期待結果】

* 9 件すべてが HTTP 200 を返す。
* `sar23` の応答が `groups` を **21 件**持つ (`docs/P001-requirement.md` §7 の 18 グループ + P102 で発見した PSI 3 グループ)。
* すべての `groups[].series[].values` の長さが、属するグループの `timestamps` の長さと一致する (INV-1)。
* `MG-CPU` の `timestamps` が **140 件以上**である。**11 件や 13 件しか無い場合は、繰り返しヘッダでブロックが切れている兆候であり FAIL とする。**
* `MG-CPU` のキー集合が `{all, 0, 1, 2}` である。
* `MG-NET` のキー数が 20 以上である。
* どの `timestamps` にも `Average` を含む文字列が無い。
* `hostname` が `www4250uj`、`cpuCount` が 3、`kind` が `"sar"`、`date` が `2026-08-23` である。
* `GET /api/metric-catalog` の `groupId` 集合が、上記 `groups` の `groupId` 集合を包含する。

## 【合否判定基準】

* 上記の期待結果をすべて満たせば PASS。1 つでも満たさなければ FAIL。

## 【失敗時に記録する内容】

* 失敗したファイル名・`groupId`・実際の値と期待値。
* とくに `timestamps` の件数が少ない場合は、その件数と、`sar` ファイル中の該当セクションのブロック数を記録する。

## 【修正禁止事項】

* アプリケーションコードを修正しない。失敗をその場で直さない。

## 【次タスクへ進む条件】

* 結果 (PASS/FAIL) を記録したら T002 へ進む。

## 重要:

* アプリケーションコードを修正しないでください。
* テスト失敗時に、その場で修正して再テストしないでください。
* テスト失敗時は、失敗内容をテスト記録に残してください。
