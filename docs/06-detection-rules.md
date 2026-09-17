# 06 — Detection Rules & Use Cases

This guide covers writing custom Wazuh detection rules for realistic security scenarios. Each rule includes the detection logic, the attack technique it maps to (MITRE ATT&CK), and a test procedure to trigger and validate it.

## How Wazuh Rules Work

Wazuh rules are XML-based and follow a hierarchy:
- **Level 0–4:** System/informational events (not alerts)
- **Level 5–9:** Low to medium severity alerts
- **Level 10–12:** High severity alerts
- **Level 13–15:** Critical alerts requiring immediate response

Rules reference existing rule IDs to chain logic. Custom rules go in `/var/ossec/etc/rules/local_rules.xml` on the Wazuh Manager.

## Custom Rule File Setup

SSH into the Wazuh Manager:

```bash
ssh labadmin@192.168.56.10
sudo nano /var/ossec/etc/rules/local_rules.xml
```

Also maintain a copy in the repo at `rules/wazuh/local_rules.xml`.

## Detection Use Cases

### Use Case 1 — Brute-Force SSH Detection

**MITRE ATT&CK:** T1110.001 (Brute Force: Password Guessing)

```xml
<!-- Alert on 5+ failed SSH attempts from the same source within 120 seconds -->
<group name="local,authentication,brute_force">
  <rule id="100001" level="10" frequency="5" timeframe="120">
    <if_matched_sid>5710</if_matched_sid>
    <same_source_ip />
    <description>SSH brute force detected: 5+ failed attempts from same source in 2 minutes</description>
    <mitre>
      <id>T1110.001</id>
    </mitre>
    <group>authentication_failures,brute_force</group>
  </rule>
</group>
```

**Test procedure:**

```bash
# From linux-endpoint, attempt multiple failed SSH logins to wazuh-server
for i in $(seq 1 6); do
  sshpass -p 'wrongpassword' ssh -o StrictHostKeyChecking=no fakeuser@192.168.56.10 2>/dev/null
done
```

### Use Case 2 — Suspicious PowerShell Execution (Windows)

**MITRE ATT&CK:** T1059.001 (Command and Scripting Interpreter: PowerShell)

```xml
<!-- Detect encoded PowerShell commands -->
<group name="local,windows,powershell">
  <rule id="100010" level="12">
    <if_sid>61600</if_sid>
    <field name="win.eventdata.scriptBlockText">\.EncodedCommand|FromBase64String|Invoke-Expression|IEX\s*\(|downloadstring</field>
    <description>Suspicious PowerShell: encoded command or download execution detected</description>
    <mitre>
      <id>T1059.001</id>
    </mitre>
    <group>powershell,suspicious_execution</group>
  </rule>

  <!-- Detect PowerShell execution policy bypass -->
  <rule id="100011" level="10">
    <if_sid>61600</if_sid>
    <field name="win.eventdata.scriptBlockText">-ExecutionPolicy\s+Bypass|-ep\s+bypass</field>
    <description>PowerShell execution policy bypass detected</description>
    <mitre>
      <id>T1059.001</id>
    </mitre>
    <group>powershell,policy_bypass</group>
  </rule>
</group>
```

**Test procedure (on win10-endpoint):**

```powershell
# Generate a benign encoded command to trigger the rule
$command = "Write-Output 'detection test'"
$encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
powershell.exe -EncodedCommand $encoded
```

### Use Case 3 — Privilege Escalation via sudo

**MITRE ATT&CK:** T1548.003 (Abuse Elevation Control: Sudo and Sudo Caching)

```xml
<group name="local,linux,privilege_escalation">
  <!-- Detect sudo usage by non-standard users -->
  <rule id="100020" level="8">
    <if_sid>5401</if_sid>
    <user negate="yes">labadmin|root</user>
    <description>Sudo executed by non-standard user — possible privilege escalation</description>
    <mitre>
      <id>T1548.003</id>
    </mitre>
    <group>privilege_escalation,sudo</group>
  </rule>

  <!-- Detect sudo to root shell -->
  <rule id="100021" level="10">
    <if_sid>5402</if_sid>
    <match>COMMAND=/bin/bash|COMMAND=/bin/sh|COMMAND=/usr/bin/su</match>
    <description>Sudo used to spawn root shell</description>
    <mitre>
      <id>T1548.003</id>
    </mitre>
    <group>privilege_escalation,root_shell</group>
  </rule>
</group>
```

### Use Case 4 — New User Account Creation

**MITRE ATT&CK:** T1136.001 (Create Account: Local Account)

```xml
<group name="local,account_management">
  <!-- Linux: new user added -->
  <rule id="100030" level="8">
    <if_sid>5902</if_sid>
    <description>New local user account created on Linux endpoint</description>
    <mitre>
      <id>T1136.001</id>
    </mitre>
    <group>account_creation</group>
  </rule>

  <!-- Windows: new user added (Event ID 4720) -->
  <rule id="100031" level="8">
    <if_sid>60106</if_sid>
    <description>New local user account created on Windows endpoint</description>
    <mitre>
      <id>T1136.001</id>
    </mitre>
    <group>account_creation</group>
  </rule>
</group>
```

**Test procedure:**

```bash
# Linux
sudo useradd -m testattacker
# Clean up after validation:
sudo userdel -r testattacker
```

```powershell
# Windows
net user testattacker P@ssw0rd123 /add
# Clean up:
net user testattacker /delete
```

### Use Case 5 — File Integrity Monitoring Alert

**MITRE ATT&CK:** T1565.001 (Data Manipulation: Stored Data Manipulation)

Configure FIM in `ossec.conf` on the manager:

```xml
<syscheck>
  <directories check_all="yes" realtime="yes">/etc,/usr/bin,/usr/sbin</directories>
  <directories check_all="yes" realtime="yes">/var/ossec/etc/rules</directories>
</syscheck>
```

Custom alert for critical file modifications:

```xml
<group name="local,file_integrity">
  <rule id="100040" level="12">
    <if_sid>550</if_sid>
    <match>/etc/passwd|/etc/shadow|/etc/sudoers</match>
    <description>Critical system file modified — potential persistence or privilege escalation</description>
    <mitre>
      <id>T1565.001</id>
    </mitre>
    <group>fim,critical_file</group>
  </rule>
</group>
```

### Use Case 6 — DLP Finding Alert

Custom rule to alert when the data scanner finds sensitive data:

```xml
<group name="local,dlp">
  <rule id="100050" level="10">
    <decoded_as>json</decoded_as>
    <field name="scan_type">pii-scan|credential-scan</field>
    <field name="severity">critical</field>
    <description>DLP scan detected critical sensitive data exposure</description>
    <group>dlp,data_exposure</group>
  </rule>

  <rule id="100051" level="8">
    <decoded_as>json</decoded_as>
    <field name="scan_type">pii-scan|credential-scan</field>
    <field name="severity">high</field>
    <description>DLP scan detected high-severity sensitive data exposure</description>
    <group>dlp,data_exposure</group>
  </rule>
</group>
```

## Apply and Test Rules

After adding rules to `local_rules.xml`:

```bash
# Validate the rule syntax
sudo /var/ossec/bin/wazuh-logtest

# If validation passes, restart the manager
sudo systemctl restart wazuh-manager
```

Use `wazuh-logtest` interactively to paste sample log lines and verify they trigger the expected rules.

## Rule Summary Table

| Rule ID | Use Case | Level | MITRE ATT&CK | Trigger |
|---|---|---|---|---|
| 100001 | SSH Brute Force | 10 | T1110.001 | 5+ failed SSH in 2 min |
| 100010 | Encoded PowerShell | 12 | T1059.001 | Base64/download in PS |
| 100011 | PS Policy Bypass | 10 | T1059.001 | -ExecutionPolicy Bypass |
| 100020 | Non-standard sudo | 8 | T1548.003 | Unexpected user runs sudo |
| 100021 | Sudo root shell | 10 | T1548.003 | sudo to bash/sh |
| 100030 | Linux account created | 8 | T1136.001 | useradd |
| 100031 | Windows account created | 8 | T1136.001 | Event 4720 |
| 100040 | Critical file modified | 12 | T1565.001 | /etc/passwd etc changed |
| 100050 | DLP critical finding | 10 | — | Scanner finds critical PII |

## Version Control

Copy the finalized rules to the repo:

```bash
cp /var/ossec/etc/rules/local_rules.xml ~/Security-Operations-Lab/rules/wazuh/
```

## Next Step

Proceed to [07 — Terraform Automation](07-terraform-automation.md) to codify the lab infrastructure.
