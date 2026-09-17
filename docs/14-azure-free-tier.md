# 14 — Azure Free Tier & SC-500 Lab

This guide sets up Microsoft's free-tier and trial offerings to practice the Azure security tools covered on the SC-500 exam. Everything here either has a free tier, a trial period, or a developer sandbox — no ongoing billing.

## What's Available for Free

| Service | How to Get It | Duration |
|---|---|---|
| Entra ID (Free tier) | Any Azure account | Permanent |
| Entra ID P2 | Trial license | 30 days |
| Microsoft 365 E5 Dev | [M365 Developer Program](https://developer.microsoft.com/en-us/microsoft-365/dev-program) | 90-day renewable sandbox |
| Defender for Endpoint P2 | Trial via M365 E5 | 90 days |
| Defender for Cloud | Free tier (CSPM) | Permanent |
| Defender for Cloud (paid plans) | 30-day trial per plan | 30 days |
| Microsoft Sentinel | 10 GB/day free ingestion | 31 days |
| Azure subscription | Free tier ($200 credit first 30 days) | 12 months free services |

## Setup Order

The key insight: the **Microsoft 365 Developer Program** is the foundation. It gives you a full E5 sandbox with Entra ID P2, Defender for Endpoint, and 25 user licenses — all free and renewable.

### Step 1 — Join the M365 Developer Program

1. Go to [developer.microsoft.com/en-us/microsoft-365/dev-program](https://developer.microsoft.com/en-us/microsoft-365/dev-program)
2. Sign up with your Microsoft account (create one if needed)
3. Choose **Instant Sandbox**
4. You get:
   - A `.onmicrosoft.com` tenant
   - 25 E5 user licenses
   - Pre-populated sample users and data
   - Entra ID P2 trial included

Save your admin credentials and tenant URL.

### Step 2 — Create an Azure Free Account

1. Go to [azure.microsoft.com/free](https://azure.microsoft.com/en-us/free/)
2. Sign up (credit card required for verification, same as AWS)
3. You get $200 credit for 30 days + 12 months of free services
4. **Set a budget immediately:**

```
Azure Portal → Cost Management → Budgets → Add
- Name: "Zero Dollar Alert"
- Amount: $1/month
- Alerts at: 50%, 80%, 100%
```

### Step 3 — Link the M365 Tenant to Azure

Your M365 developer tenant and Azure subscription should use the same Entra ID tenant. If they don't, switch directories in the Azure portal to the `.onmicrosoft.com` tenant from Step 1.

## Entra ID Exercises (SC-500: Identity Security)

### Exercise 1 — Conditional Access Policies

Conditional Access is a core SC-500 topic. In the Entra ID admin center:

```
Entra ID → Protection → Conditional Access → New Policy

Policy 1: "Require MFA for All Users"
- Users: All users (exclude break-glass admin)
- Cloud apps: All cloud apps
- Grant: Require multifactor authentication
- Enable: Report-only (test first, then On)

Policy 2: "Block Legacy Authentication"
- Users: All users
- Cloud apps: All cloud apps
- Conditions: Client apps → Exchange ActiveSync, Other clients
- Grant: Block access
- Enable: On

Policy 3: "Require Compliant Device for SOC Apps"
- Users: SOC-Tier1, SOC-Tier2 groups
- Cloud apps: Select specific apps
- Grant: Require device compliance
- Enable: Report-only
```

### Exercise 2 — Privileged Identity Management (PIM)

PIM lets you assign just-in-time, time-limited admin roles instead of standing access:

```
Entra ID → Identity Governance → Privileged Identity Management

1. Entra roles → Security Administrator → Add assignments
   - Select: sec.engineer user
   - Assignment type: Eligible (not Active)
   - Duration: 8 hours max

2. Test the flow:
   - Log in as sec.engineer
   - Go to PIM → My roles → Activate "Security Administrator"
   - Provide justification
   - Role activates for 8 hours, then auto-revokes
```

This is exactly how enterprises implement least-privilege for admin roles.

### Exercise 3 — Access Reviews

```
Entra ID → Identity Governance → Access Reviews → New

- Review name: "Quarterly SOC Access Review"
- Scope: Members of "SOC-Tier2" group
- Reviewers: specific users (iam.admin)
- Duration: 7 days
- Auto-apply results: Yes
```

Document the review process and results for your portfolio.

## Microsoft Sentinel (SC-500: Security Operations)

Sentinel is Microsoft's cloud-native SIEM. The free tier gives you 10 GB/day of ingestion for 31 days.

### Set Up Sentinel

```
Azure Portal → Microsoft Sentinel → Create
- Create a new Log Analytics Workspace
- Name: lab-sentinel-workspace
- Region: East US (or nearest)
- Pricing: Pay-as-you-go (free trial covers the first 31 days)
```

### Connect Data Sources

```
Sentinel → Data Connectors

1. Microsoft Entra ID → Connect
   - Sign-in logs, audit logs, provisioning logs

2. Microsoft 365 Defender → Connect
   - Incidents and alerts from Defender

3. Microsoft Defender for Cloud → Connect
   - Security alerts from CSPM
```

### Practice with Analytics Rules

```
Sentinel → Analytics → Rule Templates

Enable these built-in rules:
- "Brute force attack against Azure portal"
- "Suspicious sign-in from an unfamiliar location"
- "User added to privileged group"
- "MFA rejected by user"
```

### Create a Custom KQL Query

```kql
// Failed sign-ins in the last 24 hours, grouped by user
SigninLogs
| where TimeGenerated > ago(24h)
| where ResultType != "0"  // Non-zero = failure
| summarize FailureCount = count() by UserPrincipalName, IPAddress, ResultDescription
| where FailureCount > 5
| order by FailureCount desc
```

Save this as an Analytics Rule to auto-generate incidents.

### Investigate an Incident

1. Go to **Sentinel → Incidents**
2. Open any generated incident
3. Practice the investigation workflow:
   - Assign the incident to yourself
   - Set severity and status
   - Use the **Investigation Graph** to trace related entities
   - Add comments documenting your findings
   - Close with a classification (True Positive, False Positive, etc.)

## Defender for Endpoint (SC-500: Threat Protection)

Your M365 E5 sandbox includes Defender for Endpoint P2.

### Onboard a Test Machine

You can onboard your `win10-endpoint` VM to Defender for Endpoint alongside Wazuh — they coexist:

```
Microsoft Defender Portal → Settings → Endpoints → Onboarding
- Select: Windows 10/11
- Download the onboarding script
- Run the script on win10-endpoint (PowerShell as Admin)
```

### Practice EDR Workflows

1. Run the [Defender for Endpoint evaluation scenarios](https://learn.microsoft.com/en-us/defender-endpoint/evaluation-lab)
2. Practice alert triage in the Defender portal
3. Investigate device timelines, process trees, and file analysis

## Defender for Cloud (SC-500: Cloud Security Posture)

The free CSPM tier is always available:

```
Azure Portal → Microsoft Defender for Cloud → Environment Settings
- Enable free CSPM (Foundational)
- Enable 30-day trials for: Servers, Storage, SQL, Key Vault (optional)
```

### Exercise — Secure Score

1. Go to **Defender for Cloud → Secure Score**
2. Review each recommendation
3. Remediate the top 5 recommendations
4. Document your score improvement with before/after screenshots

## Cleanup and Cost Control

### Before Each Trial Expires

```
□ Day 25 of Sentinel trial: export any saved queries and analytics rules
□ Day 25 of GuardDuty trial (AWS): disable
□ Day 85 of M365 sandbox: check if it auto-renews (it usually does if active)
□ Monthly: check Azure Cost Management for any surprise charges
```

### Free Things You Can Keep Running Indefinitely

- Entra ID Free tier (users, groups, basic SSO)
- Azure free-tier VMs (B1s Linux, 750 hrs/month for 12 months)
- Defender for Cloud free CSPM
- Log Analytics Workspace (5 GB/month free ingestion after Sentinel trial)

## Portfolio Documentation

For each exercise, create a writeup in `docs/` or a separate blog post:

1. **Conditional Access Policy Design** — screenshot the policies, explain the logic, map to Zero Trust principles
2. **PIM Activation Walkthrough** — show the just-in-time flow end-to-end
3. **Sentinel Investigation** — full incident response from alert to closure with KQL queries
4. **Defender for Endpoint Alert Triage** — device timeline analysis, process tree investigation
5. **Secure Score Remediation** — before/after with specific fixes

These directly demonstrate SC-500 competency to hiring managers.

## SC-500 Exam Domain Mapping

| SC-500 Domain | Where You Practice It |
|---|---|
| Manage identity and access (25-30%) | Entra ID, Conditional Access, PIM, Okta (Guide 12), AD (Guide 11) |
| Manage security operations (25-30%) | Sentinel, Defender for Endpoint, Wazuh (Guides 02-06) |
| Manage threat protection (20-25%) | Defender for Cloud, Defender for Endpoint, GuardDuty (Guide 13) |
| Manage compliance (15-20%) | Secure Score, Defender for Cloud recommendations, CIS benchmarks |

## Next Step

Return to the [main README](../README.md) and start working through the guides in order. The local lab (Guides 01–11) should be built first — the cloud components (Guides 12–14) layer on top.
