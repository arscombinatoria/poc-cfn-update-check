# AGENT.md

このリポジトリは、CloudFormation テンプレート (`cloudformation.yml`) と、
その継続的な品質/更新チェックを行う GitHub Actions で構成されています。

## このリポジトリの目的
- CloudFormation による検証用スタックの定義（RDS / ElastiCache / Lambda）。
- `cfn-lint` によるテンプレート品質チェック。
- `cfn-lint` が持つスキーマ情報を利用した、エンジン/ランタイム更新候補の自動検知。

## 変更時の基本方針
1. **最小変更**: 目的達成に必要な最小限の差分に留める。
2. **説明可能性**: なぜ変更が必要かを README か PR 本文で説明する。
3. **再現性**: ローカルで実行できる確認手順を残す。
4. **安全性**: 本番利用を想定しない検証テンプレートである点を維持する。

## CloudFormation (`cloudformation.yml`) を変更する場合
- パラメータ互換性に注意する（既存パラメータ名の安易な変更を避ける）。
- Engine/Runtime の値を更新した場合、対応する更新検知スクリプトの前提が壊れていないか確認する。
- 可能であれば `cfn-lint cloudformation.yml` を実行する。
- 破壊的変更（リソース種別変更、置換発生の可能性が高い変更）は README へ注意事項を追記する。

## スクリプト (`.github/script/*.py`) を変更する場合
- GitHub Actions 出力（`has_update`, `issue_title`, `issue_body`, `issues`）のキー互換性を保つ。
- 文字列比較ではなくバージョン比較ロジック（`natural_version_key`）を利用する。
- 可能であれば以下を実行して最低限の品質確認を行う。
  - `python -m py_compile .github/script/check_rds_engine_updates.py`
  - `python -m py_compile .github/script/check_elasticache_engine_updates.py`
  - `python -m py_compile .github/script/check_lambda_runtime_updates.py`

## GitHub Actions (`.github/workflows/*.yml`) を変更する場合
- 既存のトリガー（`pull_request`, `schedule`, `workflow_dispatch`）の意図を維持する。
- Issue 自動作成は重複防止ロジックを維持する。
- Action のメジャーバージョン更新時は README の説明も合わせて更新する。

## 推奨ローカル確認コマンド
- `cfn-lint cloudformation.yml`
- `python .github/script/check_rds_engine_updates.py --template cloudformation.yml`
- `python .github/script/check_elasticache_engine_updates.py --template cloudformation.yml`
- `python .github/script/check_lambda_runtime_updates.py --template cloudformation.yml`

## ドキュメント運用
- README を更新する際は `README.md`（英語）と `README.ja.md`（日本語）を必ず同時に更新し、内容の整合を保つ。
- README は「初見の利用者が 5 分で概要と実行方法を理解できる」粒度を維持する。
- 新しい運用ルールを追加したら、README または本ファイルへ反映する。

