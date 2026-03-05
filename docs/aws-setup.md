# AWS Setup for StemStomp

## S3 Bucket

Create an S3 bucket for stem storage:

```bash
aws s3 mb s3://your-stemstomp-bucket
```

## IAM Policy

Create an IAM user with the minimum required permissions. Use this policy (replace `YOUR_BUCKET_NAME`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET_NAME",
                "arn:aws:s3:::YOUR_BUCKET_NAME/*"
            ]
        }
    ]
}
```

## Credential Configuration

**Option 1: Environment file (recommended for single devices)**

Add to `/opt/stemstomp/.env`:
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
```

The `.env` file is set to mode 600 (owner-only read/write) by the provisioning script.

**Option 2: AWS credentials file**

```bash
sudo -u stemstomp mkdir -p /home/stemstomp/.aws
sudo -u stemstomp bash -c 'cat > /home/stemstomp/.aws/credentials << EOF
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-east-1
EOF'
chmod 600 /home/stemstomp/.aws/credentials
```

**Option 3: IAM role (recommended for fleets)**

If running on EC2 or using IoT Greengrass, attach an IAM role directly. No credentials needed in the configuration.
