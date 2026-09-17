# Security Operations Home Lab

A local security operations environment built on VirtualBox for hands-on practice with SIEM operations, identity and access management, data loss prevention, and infrastructure-as-code automation. Designed as a portfolio project demonstrating practical security engineering skills.

## Lab Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│              Lenovo ThinkCentre M920q (Host) — 16 GB RAM            │
│                       VirtualBox Hypervisor                          │
│                                                                     │
│  TIER 1 — Always Running (10 GB) ─────────────────────────────────  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  wazuh-server     │  │  win10-endpoint   │  │  linux-endpoint  │  │
│  │  Ubuntu 22.04     │  │  Windows 10       │  │  Ubuntu 22.04    │  │
│  │                   │  │                   │  │                  │  │
│  │  • Wazuh Manager  │  │  • Wazuh Agent    │  │  • Wazuh Agent   │  │
│  │  • Wazuh Indexer  │  │  • Sysmon         │  │  • OpenDLP       │  │
│  │  • Wazuh Dashboard│  │  • Event logs     │  │  • Python scripts│  │
│  │                   │  │                   │  │                  │  │
│  │  RAM: 4 GB        │  │  RAM: 4 GB        │  │  RAM: 2 GB       │  │
│  │  Disk: 50 GB      │  │  Disk: 50 GB      │  │  Disk: 30 GB     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  TIER 2 — Swap In As Needed (+2 GB each) ─────────────────────────  │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  keycloak-server  │  │  ad-dc            │  │  vuln-target     │  │
│  │  Ubuntu 22.04     │  │  Windows Server   │  │  Metasploitable 3│  │
│  │                   │  │  2022 Eval        │  │  or DVWA on      │  │
│  │  • Keycloak 24+   │  │                   │  │  Ubuntu 22.04    │  │
│  │  • PostgreSQL 16  │  │  • AD DS / DNS    │  │                  │  │
│  │  • Nginx reverse  │  │  • GPO management │  │  • Vuln scanning │  │
│  │    proxy          │  │  • Domain join     │  │    target        │  │
│  │  RAM: 2 GB        │  │  RAM: 2 GB         │  │  RAM: 2 GB      │  │
│  │  Disk: 20 GB      │  │  Disk: 40 GB       │  │  Disk: 20 GB    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│                                                                     │
│  Network: 192.168.56.0/24 (VirtualBox Host-Only + Internal)         │
└─────────────────────────────────────────────────────────────────────┘
```

### IP Address Assignments

| VM | Hostname | IP Address | Role |
|---|---|---|---|
| Wazuh Server | `wazuh-server` | 192.168.56.10 | SIEM, log aggregation, detection engine |
| Keycloak Server | `keycloak-server` | 192.168.56.11 | Identity provider, SSO, MFA |
| AD Domain Controller | `ad-dc` | 192.168.56.12 | Active Directory DS, DNS, GPOs |
| Windows Endpoint | `win10-endpoint` | 192.168.56.20 | Monitored workstation, EDR target |
| Linux Endpoint | `linux-endpoint` | 192.168.56.21 | Data scanner, automation host |
| Vuln Target | `vuln-target` | 192.168.56.30 | Vulnerability scanning target |

## Components

### Wazuh SIEM (Log Management & Detection)
- Centralized log collection from Windows and Linux endpoints
- Custom detection rules for brute-force attacks, privilege escalation, lateral movement
- File integrity monitoring (FIM) across endpoints
- Alert triage and investigation workflows
- CIS benchmark compliance scanning

### Keycloak (Identity & Access Management)
- SSO configuration with SAML 2.0 and OIDC
- Multi-factor authentication enforcement
- Role-based access control policies
- User lifecycle management (provisioning, deprovisioning, access reviews)
- Integration with Wazuh for authentication event monitoring

### OpenDLP (Data Discovery & Classification)
- Sensitive data scanning across file systems
- PII and credential detection patterns
- Scan result reporting and remediation tracking

### Terraform (Infrastructure as Code)
- Automated VM provisioning via VirtualBox provider
- Reproducible lab environment teardown and rebuild
- Modular configuration for each lab component

### Python Automation
- Detection scripts for log analysis and anomaly identification
- Automated reporting for scan results and alert summaries
- Analysis tools for investigation support

## Hardware

**Host:** Lenovo ThinkCentre M920q (drive caddy model) — Intel Core i5-8600T (6C/6T) with vPro, 16 GB DDR4 (dual channel), 256 GB NVMe SSD, empty 2.5" SATA bay with cable for storage expansion

With 16 GB total RAM (~13 GB usable after the host OS), the lab runs on a tiered model — three VMs stay up at all times and the remaining two swap in on demand.

### Storage Note

The VM disks total ~170 GB, which leaves very little room on a 256 GB NVMe after the host OS. **Add a 2.5" SATA SSD (500 GB+) via the drive caddy before building VMs**, or point VirtualBox's default machine folder to the SATA drive and keep the host OS on the NVMe. This also keeps snapshot overhead off your boot drive.

### Tier 1 — Always Running (10 GB)

| VM | RAM | Purpose |
|---|---|---|
| `wazuh-server` | 4 GB | SIEM stack (Manager + Indexer + Dashboard) |
| `win10-endpoint` | 4 GB | Windows workstation with Sysmon and Wazuh agent |
| `linux-endpoint` | 2 GB | Linux endpoint, data scanner, automation host |

### Tier 2 — Swap In As Needed (+2 GB each)

| VM | RAM | When to Boot |
|---|---|---|
| `keycloak-server` | 2 GB | IAM exercises — SSO, MFA, RBAC, user lifecycle |
| `ad-dc` | 2 GB | Active Directory exercises — GPOs, domain join, account management |
| `vuln-target` | 2 GB | Vulnerability scanning and remediation labs |

Shut down whichever Tier 2 VM you're not using before starting the other. VirtualBox snapshots let each VM resume exactly where you left off.

**Storage:** ~170 GB across all VM disks. Keep the host OS on the 256 GB NVMe and store VMs on a 2.5" SATA SSD (500 GB+) installed in the drive caddy — this separates boot and lab workloads and gives room for snapshots.

## Getting Started

### Prerequisites

1. [VirtualBox 7.x](https://www.virtualbox.org/wiki/Downloads) installed on the host
2. [Terraform](https://developer.hashicorp.com/terraform/downloads) installed on the host
3. ISO images downloaded:
   - [Ubuntu 22.04 Server](https://releases.ubuntu.com/22.04/)
   - [Windows 10 Evaluation](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-10-enterprise)

### Setup Guides

Follow these in order:

| # | Guide | What You'll Build |
|---|---|---|
| 1 | [Host & Network Setup](docs/01-host-network-setup.md) | VirtualBox networking, host-only adapter |
| 2 | [Wazuh SIEM Deployment](docs/02-wazuh-deployment.md) | Wazuh all-in-one server on Ubuntu |
| 3 | [Endpoint Agent Enrollment](docs/03-endpoint-enrollment.md) | Wazuh agents on Windows and Linux |
| 4 | [Keycloak IAM Setup](docs/04-keycloak-setup.md) | Keycloak server with PostgreSQL |
| 5 | [OpenDLP Configuration](docs/05-opendlp-setup.md) | Data discovery scanning |
| 6 | [Detection Rules & Use Cases](docs/06-detection-rules.md) | Custom Wazuh rules and alert workflows |
| 7 | [Terraform Automation](docs/07-terraform-automation.md) | IaC for reproducible lab builds |
| 8 | [Python Automation Scripts](docs/08-python-automation.md) | Detection, reporting, and analysis tools |
| 9 | [Vulnerability Scanning Lab](docs/09-vuln-scanning.md) | Nessus Essentials scanning and remediation |
| 10 | [Investigation Walkthroughs](docs/10-investigation-walkthroughs.md) | End-to-end alert triage scenarios |
| 11 | [Active Directory Lab](docs/11-active-directory.md) | Windows Server DC, GPOs, domain-joined endpoints |
| 12 | [Okta Developer Integration](docs/12-okta-integration.md) | Okta tenant with SSO/MFA, federation with AD and Keycloak |
| 13 | [AWS Free Tier Security Lab](docs/13-aws-free-tier.md) | IAM, CloudTrail, S3 security, GuardDuty trial |
| 14 | [Azure Free Tier & SC-500 Lab](docs/14-azure-free-tier.md) | Entra ID, Defender trials, Sentinel workspace |

## Repository Structure

```
Security-Operations-Lab/
├── README.md
├── docs/                          # Step-by-step setup and walkthrough guides
│   ├── 01-host-network-setup.md
│   ├── 02-wazuh-deployment.md
│   ├── 03-endpoint-enrollment.md
│   ├── 04-keycloak-setup.md
│   ├── 05-opendlp-setup.md
│   ├── 06-detection-rules.md
│   ├── 07-terraform-automation.md
│   ├── 08-python-automation.md
│   ├── 09-vuln-scanning.md
│   ├── 10-investigation-walkthroughs.md
│   ├── 11-active-directory.md
│   ├── 12-okta-integration.md
│   ├── 13-aws-free-tier.md
│   └── 14-azure-free-tier.md
├── terraform/
│   ├── modules/                   # Reusable Terraform modules per VM
│   └── environments/
│       └── homelab/               # Lab-specific variable files
├── configs/
│   ├── wazuh/                     # Wazuh manager and agent configs
│   ├── keycloak/                  # Keycloak realm exports, theme configs
│   ├── okta/                      # Okta app configs and SAML metadata
│   └── opendlp/                   # OpenDLP scan profiles
├── rules/
│   └── wazuh/                     # Custom detection rules (XML)
├── scripts/
│   ├── detection/                 # Python detection and alerting scripts
│   ├── reporting/                 # Automated report generation
│   └── analysis/                  # Log analysis and investigation tools
└── .github/
    └── ISSUE_TEMPLATE/            # Templates for tracking lab tasks
```

## Skills Demonstrated

- **SIEM Operations:** Log ingestion, correlation, custom detection rule authoring, alert triage
- **Incident Response:** Alert investigation workflows, evidence collection, timeline reconstruction
- **Identity & Access Management:** Active Directory, Okta, Keycloak, Entra ID — SSO/OIDC/SAML, MFA, RBAC, GPOs, user lifecycle management
- **Cloud Security:** AWS IAM policies, CloudTrail monitoring, S3 bucket security, GuardDuty; Azure Entra ID, Defender for Cloud, Sentinel
- **Data Loss Prevention:** Sensitive data discovery, classification patterns, remediation tracking
- **Vulnerability Management:** Nessus scanning, prioritization, remediation, and validation
- **Infrastructure as Code:** Terraform-managed VM provisioning, modular and reproducible deployments
- **Security Automation:** Python scripting for detection engineering, reporting, and analysis
- **Compliance:** NIST CSF, CIS Controls, SOC 2 mapping, benchmark scanning and gap remediation

## Certification Alignment

This lab reinforces concepts from:
- **Microsoft SC-500** — Identity and access management, security operations, threat protection
- **CompTIA CySA+** — Security monitoring, threat detection, incident response
- **CompTIA PenTest+** — Vulnerability assessment, attack simulation

## Status

🔧 **In Progress** — Building out initial VM deployments and documentation.

## License

This project is for educational and portfolio purposes.
