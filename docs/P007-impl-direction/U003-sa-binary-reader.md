あなたはExecutor(実装担当)です。実施後は完了条件を確認し、停止条件に該当しない限り自動的に次のタスクへ進んでください。

# 【スプリントID】U003 — sa-binary-reader

**注意**: この開発環境には `sadf` が無く、導入もできない (`docs/P005-impl-plan.md` §5)。本スプリントの検証は**フィクスチャによる単体テストに限られる**。実際の `sadf` 出力での確認は行えないため、**「実 `sadf` で動作確認した」と記録してはならない。**

## タスク一覧(OKF副目次)

- [x] U003-T1 [sadf起動ラッパ](#u003-t1-sadf起動ラッパ) — subprocess の安全な呼び出しと例外変換
- [x] U003-T2 [JSON→中間表現の変換](#u003-t2-json中間表現の変換) — `sadf -j` の解釈
- [x] U003-T3 [フィクスチャによる検証](#u003-t3-フィクスチャによる検証) — 正常系・異常系

---

## U003-T1: sadf起動ラッパ

### 【目的】

* `sadf` を安全に起動し、失敗をドメイン例外へ変換する。

### 【作成・編集対象ファイル】

* `backend/app/readers/sa_binary.py`, `backend/tests/test_sadf_invoke.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §9.1 (起動条件の表)

### 【実装内容】

* `run_sadf(path, extra_args) -> str`: `subprocess.run([...], shell=False, capture_output=True, text=True, timeout=60, env={..., "LC_ALL": "C"})`。
* 引数は**必ず配列**で渡す。文字列連結・`shell=True` を使わない (REQ-N-008)。
* 例外変換:
  * `FileNotFoundError` → `SadfUnavailableError` (503)
  * `subprocess.TimeoutExpired` → `SadfFailedError` (502)
  * `returncode != 0` → `SadfFailedError` (502)。`stderr` を `detail` に載せる。
* `sadf` 実行を `event="sadf.exec"` (`argv` / `returncode` / `durationMs`) でログに記録する。
* `sadf_available() -> bool` と `sadf_version() -> str | None` も提供する (U001-T5 の health から使えるようにする)。

### 【実装してはいけないこと】

* JSON の解釈 (T2 の範囲)。

### 【Unit Test内容】

* `subprocess.run` をモックし、渡された第 1 引数が**リスト**であり `shell` が `True` でないこと。
* `env` に `LC_ALL=C` が含まれること。
* `FileNotFoundError` → `SadfUnavailableError`、`TimeoutExpired` → `SadfFailedError`、非 0 終了 → `SadfFailedError` になること。
* 非 0 終了時に `stderr` が `detail` に載ること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_sadf_invoke.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U003-T2: JSON→中間表現の変換

### 【目的】

* `sadf -j -- -A` の出力を `RawTable[]` に変換する。**U002 が確定させた中間表現に合わせる。**

### 【作成・編集対象ファイル】

* `backend/app/readers/sa_binary.py` (追記), `backend/tests/test_sa_binary.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §9.2 (JSON 構造 / ★FIXME★ 未確認), §9.3 (対応表)

### 【実装内容】

* `read_sa_binary(path) -> tuple[SarHeader, list[RawTable]]` — 戻り値の型を U002 と揃える。
* `sysstat.hosts[0]` から `nodename` / `release` / `machine` / `number-of-cpus` / `file-date` を取り、`SarHeader` を組む。
* `statistics[]` の各要素:
  * `timestamp.date` + `timestamp.time` を `YYYY-MM-DDTHH:mm:ss` に組む。
  * それ以外のキーを統計種別として走査する。`SADF_KEY_TO_GROUP` に無いキーは**無視して警告ログに出す**。
  * 値が配列ならキー付き (各要素のキー項目を `RawRow.key` に)、オブジェクトならキーなし。
  * フィールド名は `SADF_FIELD_TO_METRIC` で `sar` 表記の指標名に読み替える。**読み替えできないフィールドは無視して警告ログに出す。**
  * `network` のようにネストするキーは、`network.net-dev` の形で対応表を引く。
* 同一 `groupId` のサンプルを 1 つの `RawTable` にまとめて返す。
* **正規化は行わない。** `normalize()` (U002-T4) をそのまま使う。このスプリントで新しい正規化ロジックを作らない (REQ-F-024)。

### 【実装してはいけないこと】

* 独自の正規化・`MetricGroup` 生成。

### 【Unit Test内容】

* フィクスチャ JSON から `SarHeader` が正しく組まれること。
* キー付き統計 (`cpu-load`) が `key_label` と `key` を持つ `RawTable` になること。
* キーなし統計 (`memory`) が `key_label=None` になること。
* フィールド名が `sar` 表記に読み替えられること (`user` → `%usr`)。
* 未知の統計種別・未知のフィールドが無視され、他が失われないこと。
* ネストキー (`network.net-dev`) が解決されること。
* `read_sa_binary` の結果を `normalize()` に通して `MetricGroup[]` が得られること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_sa_binary.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U003-T3: フィクスチャによる検証

### 【目的】

* `sadf -j` 出力を模したフィクスチャを用意し、`sa` 経路を一通り検証する。

### 【作成・編集対象ファイル】

* `backend/tests/fixtures/sadf_sample.json`, `backend/tests/test_sa_pipeline.py`

### 【参照すべき仕様箇所】

* `docs/P006-test-plan.md` §6.1 (モック方針), §6.2 (`sadf` 不在時の扱い)

### 【実装内容】

* フィクスチャは**実データ `sar23` の先頭数サンプルと同じ数値**を用いて作る。将来 `sadf` が使える環境で観点 A (2 経路の一致) を実行する際の基準になるため。
* 少なくとも `cpu-load` (キー付き) / `memory` (キーなし) / `disk` (キー付き) / `network.net-dev` (ネスト) を含める。
* フィクスチャ JSON の先頭にコメント相当のメモは置けないため、`backend/tests/fixtures/README.md` に**このフィクスチャが実 `sadf` 出力ではなく仕様にもとづく再現であること**を明記する。

### 【実装してはいけないこと】

* 実 `sadf` を起動するテスト (この環境では実行できない)。

### 【Unit Test内容】

* フィクスチャ全体を `read_sa_binary` → `normalize` に通し、`MetricGroup[]` が得られること。
* `MG-CPU` の `all/%usr` の値が `sar23` の対応するサンプルと一致すること。
* すべてのグループで `len(values) == len(timestamps)` が成立すること (INV-1)。

### 【実行コマンド】

* `python -m pytest backend/tests -q` (2 回連続で同じ結果になることを確認する)

### 【完了条件】

* 上記テストが合格する。
* `docs/P007-impl-direction.md` の U003 行を `[x]` に更新する。
* **テスト記録には「`sadf` の実出力での確認は未実施」と明記する。**

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
