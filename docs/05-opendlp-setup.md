# 05 — OpenDLP Configuration

This guide covers deploying OpenDLP on the `linux-endpoint` VM for sensitive data discovery and classification.

## Overview

OpenDLP scans file systems, databases, and network shares for sensitive data patterns — credit card numbers, SSNs, API keys, credentials in plaintext. In this lab, it runs on the `linux-endpoint` (192.168.56.21) and scans both local files and shared directories across the lab network.

> **Alternative:** If you find OpenDLP's setup too dated or limiting, [Microsoft Presidio](https://github.com/microsoft/presidio) is a modern, Python-native alternative that integrates well with custom scripts. The Python automation guide (Guide 08) includes Presidio-based detection examples.

## Prerequisites

- `linux-endpoint` VM running, Wazuh agent active
- Internet access via NAT for package downloads

## Install OpenDLP

SSH into the Linux endpoint:

```bash
ssh labadmin@192.168.56.21
```

### Option A — OpenDLP (Traditional)

OpenDLP is a web-based application. Install the LAMP stack and deploy:

```bash
# Install dependencies
sudo apt install -y apache2 mysql-server php php-mysql php-curl libapache2-mod-php unzip

# Download OpenDLP
cd /opt
sudo wget https://github.com/ezarko/opendlp/archive/refs/heads/master.zip -O opendlp.zip
sudo unzip opendlp.zip
sudo mv opendlp-master opendlp
sudo chown -R www-data:www-data /opt/opendlp

# Configure MySQL database
sudo mysql << 'SQL'
CREATE DATABASE opendlp;
CREATE USER 'opendlp'@'localhost' IDENTIFIED BY 'OpenDLPLab2024!';
GRANT ALL PRIVILEGES ON opendlp.* TO 'opendlp'@'localhost';
FLUSH PRIVILEGES;
SQL

# Import the schema (path may vary — check the opendlp directory)
sudo mysql opendlp < /opt/opendlp/sql/opendlp.sql
```

Configure Apache to serve OpenDLP:

```bash
sudo tee /etc/apache2/sites-available/opendlp.conf << 'EOF'
<VirtualHost *:8443>
    DocumentRoot /opt/opendlp/web
    <Directory /opt/opendlp/web>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
EOF

sudo a2ensite opendlp
sudo a2enmod rewrite
sudo systemctl restart apache2
```

Access at `http://192.168.56.21:8443`.

### Option B — Microsoft Presidio (Recommended for Python-Based Workflows)

```bash
pip3 install presidio-analyzer presidio-anonymizer
python3 -m spacy download en_core_web_lg
```

Presidio is covered in detail in [Guide 08 — Python Automation](08-python-automation.md).

## Create Test Data

Seed the lab with synthetic sensitive data to scan against:

```bash
mkdir -p ~/test-data

# Generate fake PII files
cat > ~/test-data/employee-records.csv << 'EOF'
name,email,ssn,phone
John Doe,john@example.com,123-45-6789,555-0100
Jane Smith,jane@example.com,987-65-4321,555-0200
EOF

cat > ~/test-data/config-leak.txt << 'EOF'
# Application Config (DO NOT COMMIT)
DB_HOST=prod-db.internal
DB_PASSWORD=SuperSecret123!
AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
EOF

cat > ~/test-data/notes.txt << 'EOF'
Customer called — credit card ending in 4532 was compromised.
Reference case #8834. Customer SSN on file: 456-78-9012.
EOF
```

## Define Scan Profiles

Create scan profiles targeting different data patterns. Store the configs in the repo:

```bash
mkdir -p ~/Security-Operations-Lab/configs/opendlp
```

```bash
cat > ~/Security-Operations-Lab/configs/opendlp/scan-profiles.yaml << 'EOF'
profiles:
  - name: pii-scan
    description: Scan for personally identifiable information
    patterns:
      - name: SSN
        regex: '\b\d{3}-\d{2}-\d{4}\b'
        severity: critical
      - name: Credit Card
        regex: '\b(?:\d{4}[-\s]?){3}\d{4}\b'
        severity: critical
      - name: Email Address
        regex: '\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        severity: medium

  - name: credential-scan
    description: Scan for leaked credentials and API keys
    patterns:
      - name: AWS Access Key
        regex: 'AKIA[0-9A-Z]{16}'
        severity: critical
      - name: Generic Password
        regex: '(?i)(password|passwd|pwd)\s*[=:]\s*\S+'
        severity: high
      - name: Private Key Header
        regex: '-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----'
        severity: critical

  - name: compliance-scan
    description: Scan for data subject to regulatory requirements
    patterns:
      - name: SSN
        regex: '\b\d{3}-\d{2}-\d{4}\b'
        severity: critical
      - name: Date of Birth
        regex: '\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(19|20)\d{2}\b'
        severity: high
      - name: Medical Record Number
        regex: '(?i)MRN[\s:]*\d{6,10}'
        severity: critical
EOF
```

## Run a Scan

### Using OpenDLP Web UI

1. Navigate to `http://192.168.56.21:8443`
2. Create a new scan profile using the patterns above
3. Set the scan target to `/home/labadmin/test-data/`
4. Run the scan and review findings

### Using the Python Scanner (Preview)

A Python-based scanner script is available in `scripts/detection/`. See [Guide 08](08-python-automation.md) for the full implementation. Quick preview:

```bash
cd ~/Security-Operations-Lab
python3 scripts/detection/data_scanner.py --path ~/test-data --profile configs/opendlp/scan-profiles.yaml
```

## Forward Findings to Wazuh

Configure the scan results to generate Wazuh alerts. Create a custom log format that the Wazuh agent can ingest:

```bash
# Ensure the Wazuh agent monitors the scan output directory
sudo tee -a /var/ossec/etc/ossec.conf << 'EOF'
<localfile>
  <log_format>json</log_format>
  <location>/var/log/opendlp/scan-results.json</location>
</localfile>
EOF

sudo systemctl restart wazuh-agent
```

Custom Wazuh rules for DLP findings are covered in [Guide 06](06-detection-rules.md).

## Snapshot

```bash
VBoxManage snapshot "linux-endpoint" take "opendlp-configured" \
  --description "OpenDLP installed, scan profiles defined, test data seeded"
```

## What You've Built

- Data discovery scanner deployed on the Linux endpoint
- Scan profiles for PII, credentials, and compliance-relevant data
- Synthetic test data for safe, repeatable scanning
- Integration path to forward findings into Wazuh as security alerts

## Next Step

Proceed to [06 — Detection Rules & Use Cases](06-detection-rules.md) to write custom Wazuh detection rules.
