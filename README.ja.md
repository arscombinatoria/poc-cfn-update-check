# poc-cfn-update-check

CloudFormation テンプレート (`cloudformation.yml`) と、
その品質/更新チェックを自動化する GitHub Actions をまとめた検証用リポジトリです。

📘 English documentation: [README.md](README.md)

## 何を作るテンプレートか

`cloudformation.yml` では、以下のリソースを作成します。

- Amazon RDS for MySQL (`AWS::RDS::DBInstance`)
- Amazon ElastiCache Replication Group
  - Redis
  - Valkey
- AWS Lambda 関数
  - Node.js
  - Python
- それらで共通利用するリソース
  - Security Group
  - Subnet Group
  - Lambda 実行ロール

> [!NOTE]
> このテンプレートは学習/検証用途のサンプルです。
> そのまま本番利用する場合は、暗号化設定、可用性設計、認証情報管理、監査ログなどを別途強化してください。

---

## リポジトリ構成

```text
.
├── cloudformation.yml
├── AGENT.md
├── README.md
├── README.ja.md
└── .github
    ├── workflows
    │   ├── reviewdog-cfn-lint.yml
    │   ├── check-rds-engine-version.yml
    │   ├── check-elasticache-engine-version.yml
    │   └── check-lambda-runtime-version.yml
    └── script
        ├── check_rds_engine_updates.py
        ├── check_elasticache_engine_updates.py
        └── check_lambda_runtime_updates.py
```

---

## デプロイ例

事前に以下を準備してください。

- AWS CLI 設定済みプロファイル
- 対象 VPC
- RDS / ElastiCache 用プライベートサブネット（2 つ以上）
- Lambda を配置するサブネット

```bash
aws cloudformation deploy \
  --template-file cloudformation.yml \
  --stack-name poc-cfn-update-check \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    VpcId=vpc-xxxxxxxx \
    PrivateSubnetIds='subnet-aaaaaaa,subnet-bbbbbbb' \
    LambdaSubnetIds='subnet-aaaaaaa,subnet-bbbbbbb' \
    DBPassword='YourStrongPassword123!'
```

---

## CI/CD と自動チェック

### 1) cfn-lint（PR 時の静的チェック）

- Workflow: `.github/workflows/reviewdog-cfn-lint.yml`
- Action: `shogo82148/actions-cfn-lint`
- PR 上で cfn-lint 結果をチェックとして表示

### 2) RDS EngineVersion 更新検知

- Workflow: `.github/workflows/check-rds-engine-version.yml`
- Script: `.github/script/check_rds_engine_updates.py`
- `cfn-lint` が持つ RDS エンジンバージョン情報とテンプレートを比較し、更新候補があれば Issue 作成

### 3) ElastiCache EngineVersion 更新検知

- Workflow: `.github/workflows/check-elasticache-engine-version.yml`
- Script: `.github/script/check_elasticache_engine_updates.py`
- Redis / Valkey の EngineVersion 更新候補を検知して Issue 作成

### 4) Lambda Runtime 更新検知

- Workflow: `.github/workflows/check-lambda-runtime-version.yml`
- Script: `.github/script/check_lambda_runtime_updates.py`
- Runtime ファミリー単位（例: `nodejs*`, `python*`）で最新候補を判定し、更新候補ごとに Issue 作成

### スケジュール実行

3 つの更新検知 Workflow は日次スケジュールで実行されます（UTC cron: `0 21 * * *`）。
これは **Asia/Tokyo 06:00** に相当します。

---

## ローカルでの確認方法

```bash
# 1) 依存をインストール
python -m pip install --upgrade pip
python -m pip install cfn-lint

# 2) テンプレート lint
cfn-lint cloudformation.yml

# 3) 更新候補チェック
python .github/script/check_rds_engine_updates.py --template cloudformation.yml
python .github/script/check_elasticache_engine_updates.py --template cloudformation.yml
python .github/script/check_lambda_runtime_updates.py --template cloudformation.yml
```

---

## 変更時のガイド

- CloudFormation を変更したら、`cfn-lint` と 3 つの更新チェックを実行して挙動を確認する。
- Workflow を変更したら、README の該当説明も合わせて更新する。
- `README.md`（英語）と `README.ja.md`（日本語）は必ず同期して更新する。
- 運用ルールや作業ルールは `AGENT.md` を参照する。
