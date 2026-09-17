# Security Operations Lab — Complete Lab Checklist

Use this as a tracker as you work through each guide. Check off labs as you complete them and add links to your screenshots or writeups.

---

## Phase 1: Infrastructure Build (Guides 01–03)

### Guide 01 — Host & Network Setup
- [ ] Verify M920q hardware specs (CPU, RAM, storage)
- [ ] Enable Intel VT-x and VT-d in BIOS
- [ ] Install VirtualBox 7.x + Extension Pack
- [ ] Install 512 GB SATA SSD in drive caddy and set as default VM folder
- [ ] Create VirtualBox host-only network (192.168.56.0/24)
- [ ] Disable VirtualBox DHCP server
- [ ] Download Ubuntu 22.04 Server ISO
- [ ] Download Windows 10 Enterprise Evaluation ISO
- [ ] Download Windows Server 2022 Evaluation ISO
- [ ] Create and configure Ubuntu base VM template
- [ ] Install Ubuntu Server on base VM with SSH enabled
- [ ] Configure static IP and baseline packages on base VM
- [ ] Clone base VM → wazuh-server, keycloak-server, linux-endpoint
- [ ] Assign IPs and hostnames to each clone
- [ ] Verify all VMs can ping each other and reach the internet

### Guide 02 — Wazuh SIEM Deployment
- [ ] Allocate 4 GB RAM / 2 CPUs to wazuh-server
- [ ] Run Wazuh all-in-one installer
- [ ] Verify wazuh-manager, wazuh-indexer, wazuh-dashboard services are running
- [ ] Access Wazuh Dashboard at https://192.168.56.10
- [ ] Change default admin password
- [ ] Configure manager to listen on lab subnet
- [ ] Enable syslog and auth.log collection
- [ ] Verify Indexer health (cluster status green)
- [ ] Configure firewall rules (1514, 1515, 443, 9200)
- [ ] Take VirtualBox snapshot: "wazuh-installed-clean"

### Guide 03 — Endpoint Agent Enrollment
- [ ] Create Windows 10 VM (4 GB RAM, 2 CPUs, 50 GB disk)
- [ ] Install Windows 10 and set static IP 192.168.56.20
- [ ] Download and install Sysmon with SwiftOnSecurity config
- [ ] Verify Sysmon is logging events
- [ ] Install Wazuh agent on Windows endpoint
- [ ] Configure Sysmon, Security, System, and PowerShell event channel collection
- [ ] Enable PowerShell Script Block Logging via registry
- [ ] Assign IP 192.168.56.21 to linux-endpoint
- [ ] Install Wazuh agent on Linux endpoint
- [ ] Verify both agents show "Active" on the Wazuh Dashboard
- [ ] Generate test events (failed SSH, failed Windows login)
- [ ] Confirm test events appear in Wazuh Security Events
- [ ] Take snapshots of both endpoint VMs

---

## Phase 2: Identity & Access Management (Guides 04, 11, 12)

### Guide 04 — Keycloak IAM Setup
- [ ] Install Java JDK 17 on keycloak-server
- [ ] Install and configure PostgreSQL with Keycloak database
- [ ] Download and install Keycloak
- [ ] Configure Keycloak to use PostgreSQL and bind to lab network
- [ ] Create systemd service for persistent operation
- [ ] Access Keycloak Admin Console at http://192.168.56.11:8080
- [ ] Create "security-lab" realm
- [ ] Create RBAC roles: soc-analyst-t1, soc-analyst-t2, security-engineer, iam-admin, auditor
- [ ] Create lab users and assign roles
- [ ] Enable MFA (OTP) for the realm
- [ ] Register Wazuh Dashboard as OIDC client
- [ ] Export realm configuration to repo (configs/keycloak/)
- [ ] **Exercise: Onboarding** — provision new analyst, assign role, verify access
- [ ] **Exercise: Role Change** — promote analyst, verify expanded permissions
- [ ] **Exercise: Access Review** — generate user/role report, identify over-privilege
- [ ] **Exercise: Offboarding** — disable account, verify session termination
- [ ] Take snapshot: "keycloak-configured"

### Guide 11 — Active Directory Lab
- [ ] Create AD DC VM (Windows Server 2022, 2 GB RAM, 40 GB disk)
- [ ] Set static IP 192.168.56.12, hostname ad-dc
- [ ] Install AD DS and DNS roles
- [ ] Promote to domain controller (lab.local domain)
- [ ] Verify AD DS, DNS, and Kdc services running
- [ ] Create OUs: Security, IT, Users, Service Accounts, Workstations
- [ ] Create security team users: soc.t1, soc.t2, sec.engineer, iam.admin
- [ ] Create security groups: SOC-Tier1, SOC-Tier2, SecurityEngineers, IAMAdmins
- [ ] Join win10-endpoint to lab.local domain
- [ ] Log into win10-endpoint as a domain user
- [ ] Configure GPO: Security Audit Policy (logon, account, privilege events)
- [ ] Configure GPO: Password Policy (12 char min, lockout at 5 attempts)
- [ ] Configure GPO: Restrict Local Admin
- [ ] Install Wazuh agent on domain controller
- [ ] Configure AD-specific event channels (Security, Directory Service, PowerShell)
- [ ] Add AD detection rules to Wazuh (account lockout, privileged group change, GPO modification)
- [ ] **Exercise: Onboarding & Least Privilege** — create user, assign SOC-Tier1, verify restricted access
- [ ] **Exercise: Privilege Escalation Detection** — add user to Domain Admins, observe Wazuh alert, investigate, remediate
- [ ] **Exercise: Account Lockout Investigation** — trigger 5+ failed logins, trace source, document triage
- [ ] **Exercise: GPO Hardening Audit** — run gpresult, compare to CIS benchmark, document gaps
- [ ] Take snapshot: "ad-configured"

### Guide 12 — Okta Developer Integration
- [ ] Create free Okta developer account at developer.okta.com
- [ ] Create users mirroring AD domain users
- [ ] Create groups: SOC-Tier1, SOC-Tier2, SecurityEngineers, IAMAdmins
- [ ] Enable MFA with Okta Verify and Google Authenticator
- [ ] Set MFA enrollment policy to Required
- [ ] Register Wazuh Dashboard as SAML 2.0 app
- [ ] Configure attribute statements (roles → groups)
- [ ] Download IdP metadata XML
- [ ] Register Keycloak as OIDC app for federation
- [ ] Configure Keycloak Identity Provider for Okta (Login with Okta)
- [ ] **Exercise: SSO Login Flow** — log into Wazuh via Okta, screenshot entire SAML chain
- [ ] **Exercise: Federated Login** — log into Keycloak via Okta, document JIT provisioning
- [ ] **Exercise: Access Review Report** — run Python script, generate user/group report, identify issues
- [ ] **Exercise: IdP Comparison Writeup** — compare AD vs Okta vs Keycloak strengths and use cases

---

## Phase 3: Detection Engineering (Guides 05, 06)

### Guide 05 — OpenDLP Configuration
- [ ] Install OpenDLP or Microsoft Presidio on linux-endpoint
- [ ] Create synthetic test data (fake PII, credentials, config files)
- [ ] Configure scan profiles: pii-scan, credential-scan, compliance-scan
- [ ] Run PII scan against test data directory
- [ ] Run credential scan against test data directory
- [ ] Review scan findings and verify detection accuracy
- [ ] Configure Wazuh agent to monitor scan output directory
- [ ] Verify DLP findings appear as Wazuh alerts

### Guide 06 — Detection Rules & Use Cases
- [ ] **Rule 100001: SSH Brute Force** — write rule, test with 6 rapid failed SSH attempts, validate alert
- [ ] **Rule 100010: Encoded PowerShell** — write rule, test with Base64 encoded command, validate alert
- [ ] **Rule 100011: PS Policy Bypass** — write rule, test with -ExecutionPolicy Bypass, validate alert
- [ ] **Rule 100020: Non-standard sudo** — write rule, test with unexpected user, validate alert
- [ ] **Rule 100021: Sudo root shell** — write rule, test with sudo bash, validate alert
- [ ] **Rule 100030: Linux account created** — write rule, test with useradd, validate alert
- [ ] **Rule 100031: Windows account created** — write rule, test with net user /add, validate alert
- [ ] **Rule 100040: Critical file modified** — configure FIM, modify /etc/passwd, validate alert
- [ ] **Rule 100050: DLP critical finding** — trigger via data scanner, validate alert
- [ ] **Rule 100060: AD account lockout** — trigger lockout, validate alert (requires Guide 11)
- [ ] **Rule 100061: Privileged group change** — add user to Domain Admins, validate alert
- [ ] **Rule 100062: GPO modified** — modify a GPO, validate alert
- [ ] Test all rules with wazuh-logtest
- [ ] Copy finalized local_rules.xml to repo

---

## Phase 4: Automation & IaC (Guides 07, 08)

### Guide 07 — Terraform Automation
- [ ] Install Terraform on host machine
- [ ] Review the ubuntu-vm module (main.tf, variables.tf, outputs.tf)
- [ ] Configure terraform.tfvars with ISO paths
- [ ] Run terraform init
- [ ] Run terraform plan and review output
- [ ] Run terraform apply to create VMs
- [ ] Verify VMs were created correctly
- [ ] Run terraform destroy to tear down
- [ ] Rebuild with terraform apply to prove reproducibility

### Guide 08 — Python Automation Scripts
- [ ] **Data Scanner (data_scanner.py)** — run against test data, review findings
- [ ] **Alert Analyzer (alert_analyzer.py)** — query Wazuh Indexer, generate triage summary
- [ ] **Okta Lifecycle Script** — provision user, run access review, offboard user via API
- [ ] Write a custom reporting script that generates a weekly security summary
- [ ] Write an analysis script for log anomaly detection

---

## Phase 5: Vulnerability Management (Guide 09)

### Guide 09 — Vulnerability Scanning Lab
- [ ] Create vuln-target VM (Metasploitable 3 or DVWA on Ubuntu, 2 GB RAM)
- [ ] Install Nessus Essentials on linux-endpoint (free, 16 IPs)
- [ ] Register for Nessus Essentials activation code at tenable.com
- [ ] Configure Nessus scan targets (all lab VMs)
- [ ] Run a Basic Network Scan against the lab network
- [ ] Run a credentialed scan against the vuln-target
- [ ] Review and prioritize findings by CVSS score
- [ ] Remediate the top 5 critical/high vulnerabilities
- [ ] Re-scan to validate remediation
- [ ] Export scan results and document remediation steps
- [ ] Write a vulnerability assessment report for the portfolio

---

## Phase 6: Investigation & Triage (Guide 10)

### Guide 10 — Investigation Walkthroughs
- [ ] **Scenario 1: Brute Force → Account Compromise** — trigger SSH brute force, simulate successful login, investigate full kill chain in Wazuh
- [ ] **Scenario 2: Malicious PowerShell Execution** — run encoded PS on Windows, trace alert through Sysmon and Wazuh, document timeline
- [ ] **Scenario 3: Insider Threat — Privilege Escalation** — unauthorized user added to Domain Admins, investigate who/when/how, document incident response
- [ ] **Scenario 4: Data Exfiltration Attempt** — DLP scanner detects sensitive data in unauthorized location, trace how it got there, document remediation
- [ ] **Scenario 5: Compromised Credentials** — simulate credential theft via failed MFA, investigate Okta/Keycloak logs alongside Wazuh, document response
- [ ] Write each scenario as a full incident report (timeline, evidence, impact, remediation, lessons learned)

---

## Phase 7: Cloud Security (Guides 13, 14)

### Guide 13 — AWS Free Tier Security Lab
- [ ] Create AWS Free Tier account
- [ ] Set up zero-spend budget alert immediately
- [ ] Set up $1/month budget alert as backup
- [ ] Create IAM admin user, enable MFA on root and admin
- [ ] Never log in as root again
- [ ] **Exercise: Least-Privilege IAM** — write SOCAnalystReadOnly policy, create users, test access boundaries
- [ ] **Exercise: IAM Access Analyzer** — create analyzer, review findings, remediate
- [ ] **Exercise: CloudTrail Investigation** — filter events by user/action, trace your own activity
- [ ] **Exercise: S3 Bucket Hardening** — create bucket, block public access, enable versioning
- [ ] **Exercise: S3 Misconfiguration & Fix** — create permissive policy, detect with Access Analyzer, remediate, document
- [ ] Enable GuardDuty 30-day trial
- [ ] Generate sample findings in GuardDuty
- [ ] Triage 3–5 GuardDuty finding types and document investigation workflow
- [ ] Disable GuardDuty before trial ends
- [ ] Run cleanup checklist

### Guide 14 — Azure Free Tier & SC-500 Lab
- [ ] Join Microsoft 365 Developer Program (free E5 sandbox)
- [ ] Create Azure Free account
- [ ] Set $1/month budget alert immediately
- [ ] Link M365 tenant to Azure subscription
- [ ] **Exercise: Conditional Access — Require MFA** — create policy, test in report-only, then enable
- [ ] **Exercise: Conditional Access — Block Legacy Auth** — create policy, enable
- [ ] **Exercise: Conditional Access — Require Compliant Device** — create policy for SOC apps
- [ ] **Exercise: PIM Just-In-Time Roles** — assign eligible Security Admin role, activate with justification, observe auto-revoke
- [ ] **Exercise: Access Reviews** — create quarterly SOC access review, assign reviewer, complete review
- [ ] Set up Microsoft Sentinel workspace
- [ ] Connect Entra ID, M365 Defender, and Defender for Cloud data sources
- [ ] Enable built-in analytics rules (brute force, unfamiliar location, privileged group, MFA rejection)
- [ ] **Exercise: Custom KQL Query** — write failed sign-in detection query, save as analytics rule
- [ ] **Exercise: Sentinel Incident Investigation** — assign, investigate with graph, document findings, close with classification
- [ ] Onboard win10-endpoint to Defender for Endpoint
- [ ] **Exercise: EDR Alert Triage** — investigate device timeline, process tree, file analysis
- [ ] Enable Defender for Cloud free CSPM
- [ ] **Exercise: Secure Score Remediation** — review recommendations, fix top 5, document before/after scores
- [ ] Run cleanup checklist before trials expire

---

## Portfolio Documentation Checklist

For each completed exercise, capture:

- [ ] Screenshots of key steps and results
- [ ] Written walkthrough explaining what you did and why
- [ ] Incident reports for investigation scenarios (timeline, evidence, impact, remediation)
- [ ] Commit all documentation, configs, and scripts to GitHub
- [ ] Keep README status section updated as you complete guides

### High-Impact Portfolio Pieces (Prioritize These)

- [ ] Wazuh detection rules with MITRE ATT&CK mappings and test procedures
- [ ] Full incident investigation writeup with timeline and evidence
- [ ] IAM comparison writeup (AD vs Okta vs Keycloak vs Entra ID)
- [ ] Conditional Access + PIM walkthrough (SC-500 gold)
- [ ] Vulnerability assessment report with remediation validation
- [ ] Python automation scripts with clean code and documentation
- [ ] Terraform modules demonstrating IaC principles
