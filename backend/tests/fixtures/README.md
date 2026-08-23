# テストフィクスチャ

## `sadf_sample.json`

**このファイルは実際の `sadf -j` の出力ではない。** sysstat の公開仕様にもとづいて
再現した JSON である。

理由: 本プロジェクトを開発した環境には `sadf` が無く、導入もできなかった
(Windows には sysstat が無く、WSL の `sudo` がパスワードを要求するため非対話で
インストールできない)。詳細は `docs/ArchitectureHandbook.md` §9-1 を参照。

数値は実データ `sysstat-log/var/log/sysstat/sar23` の先頭サンプルと一致させてある。
将来 `sadf` が使える環境で「2 経路の一致」(P008 T002) を実行する際の基準になるため。

**`sadf` が使える環境で最初に実行する際は、実際の出力と本ファイルの構造を突き合わせ、
相違があれば `backend/app/metrics/catalog.py` の対応表と
`docs/P003-backend-spec.md` §9.2/§9.3 を修正すること。**
