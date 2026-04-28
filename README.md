# poc-cfn-update-check

This repository is a proof-of-concept for a CloudFormation template (`cloudformation.yml`) and GitHub Actions that automate quality checks and version-update detection.

📘 Japanese documentation: [README.ja.md](README.ja.md)

## What this template provisions

`cloudformation.yml` creates the following resources:

- Amazon RDS for MySQL (`AWS::RDS::DBInstance`)
- Amazon ElastiCache Replication Groups
  - Redis
  - Valkey
- AWS Lambda functions
  - Node.js
  - Python
- Shared networking and IAM resources
  - Security Group
  - Subnet Groups
  - Lambda execution role

> [!NOTE]
> This is a sample template for learning and validation.
> If you use it in production, harden security, availability, secret management, and observability settings.

---

## Repository layout

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

## Deployment example

Prerequisites:

- AWS CLI configured
- Target VPC
- Two or more private subnets for RDS and ElastiCache
- Subnets for Lambda VPC execution

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

## CI and automated checks

### 1) cfn-lint on pull requests

- Workflow: `.github/workflows/reviewdog-cfn-lint.yml`
- Action: `shogo82148/actions-cfn-lint`
- Reports template lint findings as PR checks

### 2) RDS engine version update checks

- Workflow: `.github/workflows/check-rds-engine-version.yml`
- Script: `.github/script/check_rds_engine_updates.py`
- Compares template `EngineVersion` values with cfn-lint schema data and opens an issue when newer versions are found

### 3) ElastiCache engine version update checks

- Workflow: `.github/workflows/check-elasticache-engine-version.yml`
- Script: `.github/script/check_elasticache_engine_updates.py`
- Detects Redis/Valkey `EngineVersion` updates and opens an issue when needed

### 4) Lambda runtime update checks

- Workflow: `.github/workflows/check-lambda-runtime-version.yml`
- Script: `.github/script/check_lambda_runtime_updates.py`
- Detects latest runtimes by family (for example `nodejs*`, `python*`) and opens issues for updatable resources

### Scheduled runs

The three update-check workflows run daily on UTC cron `0 21 * * *`.
That corresponds to **06:00 Asia/Tokyo**.

---

## Local validation

```bash
# 1) Install dependencies
python -m pip install --upgrade pip
python -m pip install cfn-lint

# 2) Lint template
cfn-lint cloudformation.yml

# 3) Check version/runtime updates
python .github/script/check_rds_engine_updates.py --template cloudformation.yml
python .github/script/check_elasticache_engine_updates.py --template cloudformation.yml
python .github/script/check_lambda_runtime_updates.py --template cloudformation.yml
```

---

## Contribution notes

- Run `cfn-lint` and the three update-check scripts when changing the template.
- Keep workflow behavior and documentation aligned when editing `.github/workflows/*`.
- Keep `README.md` (English) and `README.ja.md` (Japanese) in sync.
- See `AGENT.md` for detailed contributor/automation guidance.
