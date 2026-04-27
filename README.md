# poc-cfn-update-check

This repository includes `cloudformation.yml`, a sample AWS CloudFormation template.

The template provisions:
- Amazon RDS for MySQL
- Amazon ElastiCache for Redis (Replication Group)
- AWS Lambda functions (Node.js and Python)

## Example deployment

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
