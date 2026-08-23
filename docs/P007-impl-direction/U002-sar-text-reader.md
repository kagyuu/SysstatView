あなたはExecutor(実装担当)です。以下は1スプリント分の作業範囲と完了条件を定義したものです。実施後は、そのタスクの完了条件を満たしたことを確認したうえで、Executor Stepの「停止条件」に該当しない限り、自動的に次のタスクへ進んでください。

# 【スプリントID】U002 — sar-text-reader

**本スプリントは本システムの中核である。** `sar` テキストの解析は実装が最も誤りやすく、かつこの開発環境で実データによる完全な検証ができる唯一の経路である。ここで中間表現と正規化を固めれば、U003 (`sa` 経路) はその型に合わせるだけになる。

## タスク一覧(OKF副目次)

- [x] U002-T1 [中間表現の定義](#u002-t1-中間表現の定義) — `RawTable` / `RawRow`
- [x] U002-T2 [ヘッダ行の解析](#u002-t2-ヘッダ行の解析) — 1行目から日付・ホスト情報を取る
- [x] U002-T3 [ブロック分割とデータ行解析](#u002-t3-ブロック分割とデータ行解析) — 繰り返しヘッダと`Average:`の処理
- [x] U002-T4 [正規化と不変条件](#u002-t4-正規化と不変条件) — `RawTable[]` → `MetricGroup[]`
- [x] U002-T5 [実データによる検証](#u002-t5-実データによる検証) — `sar15`〜`sar23` を通す

---

## U002-T1: 中間表現の定義

### 【目的】

* 2 経路の差異をリーダ層の内部に閉じ込めるための共通中間表現を定義する (REQ-F-024 を構造で保証する)。

### 【作成・編集対象ファイル】

* `backend/app/readers/__init__.py`, `backend/app/readers/raw.py`, `backend/tests/test_raw.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §7.2 (中間表現)

### 【実装内容】

* `RawRow`: `timestamp: str` (`YYYY-MM-DDTHH:mm:ss`) / `key: str | None` / `values: dict[str, float | None]`。
* `RawTable`: `columns: list[str]` (キー列を除く) / `key_label: str | None` / `rows: list[RawRow]`。
* `dataclass` で実装する。Pydantic モデルにしない (API に露出しないため)。

### 【実装してはいけないこと】

* 解析ロジック (T2/T3 の範囲)。

### 【Unit Test内容】

* `RawTable` / `RawRow` を生成でき、フィールドが期待どおりであること。
* `values` に `None` を格納できること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_raw.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U002-T2: ヘッダ行の解析

### 【目的】

* `sar` ファイルの 1 行目から採取日・ホスト名・カーネル・アーキテクチャ・CPU 数を取り出す。ファイル全体を読まずに採取日だけ取れる関数も併せて用意する (REQ-N-016)。

### 【作成・編集対象ファイル】

* `backend/app/readers/sar_text.py`, `backend/tests/test_sar_header.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §6.2 (`sar` の採取日抽出), §8.2 #7
* `docs/P001-requirement.md` §2.1(c) (1 行目の実例)

### 【実装内容】

* 1 行目の実例:
  `Linux 6.8.0-106-generic (www4250uj) \t2026-08-23 \t_x86_64_\t(3 CPU)`
* `SarHeader` dataclass: `date: date` / `hostname: str|None` / `kernel: str|None` / `arch: str|None` / `cpu_count: int|None`。
* `parse_header_line(line) -> SarHeader`: 正規表現で抽出する。
  * 日付: `(\d{4})-(\d{2})-(\d{2})` を優先。合致しなければ `MM/DD/YYYY` 形式も試す ★FIXME★ (ISO 以外の実データ未入手)
  * ホスト名 `\(([^)]+)\)` の最初の一致、カーネル `^Linux\s+(\S+)`、arch `_([^_\s]+)_`、CPU 数 `\((\d+)\s+CPU\)`
  * **ホスト名の抽出は `(3 CPU)` にも合致しうるため、最初の括弧のみを採る。**
* `read_header(path) -> SarHeader`: **1 行目のみを読む。** ファイル全体を読み込まない。
* 日付を抽出できない場合は `ParseFailedError` を投げる。

### 【実装してはいけないこと】

* データ行の解析 (T3 の範囲)。

### 【Unit Test内容】

* 実例の 1 行目から日付・ホスト名・カーネル・arch・CPU 数が正しく取れること。
* ホスト名として `3 CPU` を誤って拾わないこと。
* 日付が無い行で `ParseFailedError` になること。
* `read_header` が実データ `sar23` に対して `2026-08-23` / `www4250uj` / `3` を返すこと。
* `read_header` が 1 行目だけを読むこと (巨大ファイルでも全読み込みしないこと。ファイルオブジェクトの読み込み量で確認するか、`readline` の使用をもって確認する)。

### 【実行コマンド】

* `python -m pytest backend/tests/test_sar_header.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U002-T3: ブロック分割とデータ行解析

### 【目的】

* `sar` テキストの本体を `RawTable[]` に変換する。**本スプリント最大の要点。**

### 【作成・編集対象ファイル】

* `backend/app/readers/sar_text.py` (追記), `backend/tests/test_sar_text.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §8 (解析アルゴリズムと実装上の要点の表)
* `docs/P001-requirement.md` §2.1(c)

### 【実装内容】

* `read_sar_text(path) -> tuple[SarHeader, list[RawTable]]`。
* 走査規則 (実データで確認済みの事実にもとづく):
  1. **空行の直後の行は必ず「列名ヘッダ行」である。** 行の内容から推測しない。
  2. 列名ヘッダ行の 1 列目は時刻または `Average:`。2 列目が `CPU` / `DEV` / `IFACE` / `TTY` のいずれかならキー付きで、`columns` は 3 列目以降。そうでなければキーなしで `columns` は 2 列目以降。
  3. **`Average:` で始まる行はデータ行として採用しない。** ヘッダ行を伴う点に注意する。
  4. データ行は `str.split()` (連続空白で分割) で分ける。
  5. 数値化できない値は `None` とする。**行ごと捨てない。**
  6. 値の個数が `columns` の個数と一致しない行は破損行として読み飛ばし、警告ログに出す。
  7. 時刻は `HH:MM:SS` と `HH:MM:SS AM/PM` の両方を受理する。
  8. 日付はヘッダから得た日付を用いる。**時刻が直前の行より巻き戻った場合は日付を 1 日進める。**
* **同一の列構成を持つブロックは、この時点では別々の `RawTable` として返してよい。** 連結は T4 の正規化が行う。
* 空行が連続する場合・末尾の空行を正しく扱う。

### 【実装してはいけないこと】

* `groupId` の判定 (T4 の範囲。ここでは列名のまま保持する)。

### 【Unit Test内容】

* **繰り返しヘッダ**: 同一列構成のブロックが 2 つ以上ある入力で、両方のブロックのデータ行が取得できること (どちらかが失われないこと)。
* **`Average:` の除外**: `Average:` ブロックの行が `RawTable.rows` に含まれないこと。
* **空行をセクション境界と誤認しない**: 空行の直後を必ずヘッダ行として扱うこと。
* キー付き判定: 2 列目が `CPU`/`DEV`/`IFACE`/`TTY` のとき `key_label` が設定され、`columns` が 3 列目以降になること。
* キーなし判定: 2 列目が上記以外のとき `key_label` が `None` になること。
* 数値化: `-` や空文字が `None` になり、その行の他の値は保持されること。
* 破損行: 値の個数が合わない行が読み飛ばされ、他の行に影響しないこと。
* AM/PM: `01:50:00 PM` が 13:50:00 として解釈されること。
* 日跨ぎ: 時刻が巻き戻ったとき日付が 1 日進むこと。
* 上記はすべて**テスト内で組み立てた小さなテキスト**で検証する (実データ全体を使わない)。

### 【実行コマンド】

* `python -m pytest backend/tests/test_sar_text.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U002-T4: 正規化と不変条件

### 【目的】

* `RawTable[]` を API 応答の `MetricGroup[]` に変換し、不変条件を検証する。

### 【作成・編集対象ファイル】

* `backend/app/readers/normalize.py`, `backend/tests/test_normalize.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §7.3 (正規化手順), §4.2 (INV-1〜INV-5)

### 【実装内容】

* `normalize(tables: list[RawTable]) -> list[MetricGroup]`。
* 手順:
  1. 各 `RawTable` の `columns` と `key_label` から `identify_group_from_sar` で `groupId` を決める。判定できない表は**無視して警告ログに出す** (未知のグループがあってもファイル全体の読み取りを失敗させない)。
  2. **同一 `groupId` の表の `rows` を連結する** (繰り返しヘッダ由来のブロック分割を吸収する)。
  3. `timestamps` = 全 `rows` の `timestamp` を昇順・重複排除。
  4. 各 `(key, metric)` について `timestamps` と同長の `values` を作る。該当サンプルが無い添字は `None`。
  5. INV-1〜INV-5 を検証し、違反時は `AppError` (`INTERNAL_ERROR`) を投げる。
  6. `GroupDef.displayOrder` で並べる。
* `series` が空のグループは結果に含めない (INV-5)。
* `unit` は `unit_for(metric)` で決める。

### 【実装してはいけないこと】

* `sar` 固有の処理をここに書くこと (`sa` 経路も同じ関数を使うため)。

### 【Unit Test内容】

* 同一 `groupId` の 2 つの `RawTable` が 1 つの `MetricGroup` に連結されること。
* `values` の長さが `timestamps` の長さと一致すること (INV-1)。
* `timestamps` が昇順・重複なしであること (INV-2)。
* 一部のキーにだけ存在するサンプルが `None` で埋まること。
* `keyLabel=None` のグループの `series[].key` がすべて `None` であること (INV-3)。
* 未知の列構成の表が無視され、他のグループが返ること。
* 空の `series` を持つグループが結果に含まれないこと (INV-5)。
* INV 違反を意図的に作り、例外が投げられること。
* 出力順が `displayOrder` に従うこと。

### 【実行コマンド】

* `python -m pytest backend/tests/test_normalize.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U002-T5: 実データによる検証

### 【目的】

* 合成データではなく**実データ**で `sar` 経路が通ることを確認する。この開発環境で完全に検証できる唯一の経路であり、ここは妥協しない。

### 【作成・編集対象ファイル】

* `backend/tests/test_sar_realdata.py`

### 【参照すべき仕様箇所】

* `docs/P006-test-plan.md` §2 観点 B, §5 (実データを書き換えない)

### 【実装内容】

* `sysstat-log/var/log/sysstat/sar15`〜`sar23` の全 9 件を対象にする。
* 各ファイルについて `read_sar_text` → `normalize` を通し、結果を検証する。

### 【実装してはいけないこと】

* 実データファイルの書き換え。

### 【Unit Test内容】

* 9 ファイルすべてが例外なく解析できること。
* `sar23` の採取日が `2026-08-23`、ホスト名が `www4250uj`、CPU 数が 3 であること。
* `sar23` から **21 グループ**が得られること (`docs/P001-requirement.md` §7 の一覧 18 + P102 で実データから発見した PSI 3 グループ)。
* `MG-CPU` のキーが `{all, 0, 1, 2}` であること。
* `MG-CPU` の `timestamps` が **144 件前後**であること (1 日 ≒ 10 分間隔)。**11 件や 13 件しか無い場合は、繰り返しヘッダでブロックが切れている兆候であり不合格**とする。
* すべてのグループで `len(values) == len(timestamps)` が成立すること。
* どの `series` にも `Average` 由来の値が混入していないこと (`timestamps` に `Average` を含む文字列が無いこと)。
* `MG-NET` のキー数が 20 以上であること (Docker 由来のインタフェースを取りこぼしていないこと)。
* `MG-CPU` の最初のサンプルの `all/%usr` が実ファイルの記載値と一致すること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_sar_realdata.py -q`
* 続けて `python -m pytest backend/tests -q` を **2 回連続で実行**し、同じ結果になることを確認する (REQ-N-014)。

### 【完了条件】

* 上記テストがすべて合格する。
* スプリント全体のテストを 2 回続けて実行し、同じ結果になる。
* `docs/P007-impl-direction.md` の U002 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
