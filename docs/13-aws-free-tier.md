# 13 — AWS Free Tier Security Lab

This guide walks through setting up an AWS Free Tier account with billing guardrails, then practicing cloud security fundamentals — IAM policies, CloudTrail, S3 bucket security, and a GuardDuty trial — without incurring charges.

## Billing Safety First

This is the most important section. Read it before creating the account.

### What's Actually Free

| Service | Free Tier | Duration |
|---|---|---|
| IAM | Always free | Permanent |
| CloudTrail (1 trail) | Always free | Permanent |
| S3 | 5 GB storage, 20K GET, 2K PUT/month | 12 months |
| VPC | Always free (no NAT Gateway) | Permanent |
| GuardDuty | 30-day trial | One-time |
| Security Hub | 30-day trial | One-time |
| Config | 0 rule evaluations | 12 months |

### What Will Surprise-Bill You

- **NAT Gateways** — $0.045/hr (~$32/month). Never create one.
- **Elastic IPs** not attached to a running instance — $0.005/hr
- **EC2 instances** left running past free tier hours
- **S3** if you accidentally enable logging to itself (infinite loop)
- **Config rules** beyond the free tier count
- **Any service not listed above** — assume it costs money

### Set Up Billing Guardrails Immediately

Do these within 5 minutes of account creation:

```
1. AWS Console → Billing → Budgets → Create Budget
   - Budget type: Zero spend budget
   - Name: "Zero Dollar Alert"
   - Email: your email
   → This alerts you the instant ANY charge appears

2. AWS Console → Billing → Budgets → Create Budget
   - Budget type: Cost budget
   - Amount: $1.00 / Monthly
   - Alert at 80% ($0.80) and 100% ($1.00)
   → Backup alert if something accrues slowly

3. AWS Console → Account → Account Settings
   - Verify "IAM User and Role Access to Billing" is enabled
   → So you can monitor from a non-root user
```

### The Nuclear Option

If anything goes wrong:

1. **Billing → Bills** — check for charges immediately
2. Delete whatever resource is generating the charge
3. If unsure, **close the account** — AWS prorates charges on closure
4. You can contest unexpected charges via AWS Support (they're usually reasonable about free-tier accidents)

## Create the AWS Account

1. Go to [aws.amazon.com/free](https://aws.amazon.com/free/)
2. Create a personal account with your email
3. **Credit card is required** — AWS validates it with a $1 temporary hold that's refunded
4. Select the **Basic (Free)** support plan
5. **Immediately** set up the billing guardrails above

## IAM Security Exercises

IAM is always free and is the single most important AWS security skill.

### Exercise 1 — Never Use Root Again

```bash
# Create an admin IAM user (do this from root, then never log in as root again)
# AWS Console → IAM → Users → Create User

# User: lab-admin
# Access: AWS Management Console access
# Attach policy: AdministratorAccess (for lab setup only)
# Enable MFA on the root account AND this admin user
```

### Exercise 2 — Least-Privilege IAM Policies

Create custom policies that enforce least privilege:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SOCAnalystReadOnly",
      "Effect": "Allow",
      "Action": [
        "guardduty:Get*",
        "guardduty:List*",
        "securityhub:Get*",
        "securityhub:List*",
        "cloudtrail:LookupEvents",
        "cloudtrail:GetTrailStatus",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyBillingChanges",
      "Effect": "Deny",
      "Action": [
        "aws-portal:Modify*",
        "budgets:Modify*"
      ],
      "Resource": "*"
    }
  ]
}
```

Create IAM users that mirror your lab roles:

| IAM User | Policy | Maps To |
|---|---|---|
| `soc-analyst` | SOCAnalystReadOnly (above) | SOC Tier 1 |
| `security-engineer` | SecurityAudit + custom | Security Engineer |
| `iam-admin` | IAMFullAccess | IAM Administrator |

### Exercise 3 — IAM Access Analyzer

```
IAM → Access Analyzer → Create Analyzer
- Type: Account
- Name: lab-access-analyzer
```

Access Analyzer identifies resources shared outside your account (public S3 buckets, cross-account roles). Run it and document findings — even in a new account there may be default resources flagged.

## CloudTrail (Free — 1 Management Trail)

```
CloudTrail → Create Trail
- Trail name: lab-security-trail
- Storage location: Create new S3 bucket (auto-named)
- Log file SSE-KMS encryption: No (keeps it free-tier)
- CloudWatch Logs: Skip (costs money)
- Management events: Read + Write
```

### Exercise — Investigate Your Own Activity

After creating IAM users and policies:

```
CloudTrail → Event History → Filter by:
- Event name: CreateUser, AttachUserPolicy, CreatePolicy
- User name: lab-admin
```

Practice reading CloudTrail events — who did what, when, from which IP. This is the same skill as investigating insider threats or compromised credentials.

## S3 Bucket Security (Free — 5 GB)

### Exercise 1 — Create and Harden a Bucket

```bash
# Using AWS CLI (install: pip install awscli)
aws s3 mb s3://lab-security-YOURNAME --region us-east-1

# Block all public access (should be default but verify)
aws s3api put-public-access-block \
  --bucket lab-security-YOURNAME \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

# Enable versioning (free, protects against accidental deletion)
aws s3api put-bucket-versioning \
  --bucket lab-security-YOURNAME \
  --versioning-configuration Status=Enabled
```

### Exercise 2 — Create a Deliberately Misconfigured Bucket (Then Fix It)

```bash
# Create a bucket with a permissive policy (DON'T put real data in this)
aws s3 mb s3://lab-insecure-test-YOURNAME --region us-east-1

# Apply an overly permissive bucket policy
aws s3api put-bucket-policy --bucket lab-insecure-test-YOURNAME --policy '{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicRead",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::lab-insecure-test-YOURNAME/*"
  }]
}'

# Now detect it with Access Analyzer and remediate
# IAM → Access Analyzer → Findings → should show the public bucket

# Fix it:
aws s3api delete-bucket-policy --bucket lab-insecure-test-YOURNAME
aws s3api put-public-access-block --bucket lab-insecure-test-YOURNAME \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Document the finding, investigation, and remediation as an incident response writeup.

## GuardDuty (30-Day Free Trial)

```
GuardDuty → Get Started → Enable GuardDuty
```

GuardDuty analyzes CloudTrail, VPC Flow Logs, and DNS logs for threats. During the 30-day trial:

- Generate sample findings: **GuardDuty → Settings → Generate Sample Findings**
- Practice triaging each finding type
- Document your investigation workflow for 3–5 finding types

**Important:** Disable GuardDuty before the 30-day trial ends to avoid charges:

```
GuardDuty → Settings → Suspend GuardDuty → Disable GuardDuty
```

## Cleanup Checklist

Run this before you step away from the AWS account for extended periods:

```
□ GuardDuty disabled (if past 30 days)
□ Security Hub disabled (if past 30 days)
□ No running EC2 instances
□ No NAT Gateways
□ No unattached Elastic IPs
□ S3 buckets: only the CloudTrail bucket and lab buckets remain
□ Billing dashboard shows $0.00
```

## What to Screenshot for Your Portfolio

- IAM policy JSON showing least-privilege design
- CloudTrail event investigation walkthrough
- Access Analyzer findings with remediation
- S3 bucket hardening before/after
- GuardDuty finding triage (use the sample findings)

## Next Step

Proceed to [14 — Azure Free Tier & SC-500 Lab](14-azure-free-tier.md) for Microsoft-specific security tooling.
