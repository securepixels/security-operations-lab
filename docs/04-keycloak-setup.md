# 04 — Keycloak IAM Setup

This guide deploys Keycloak as the lab's identity provider on the `keycloak-server` VM (192.168.56.11). You'll configure SSO, MFA, RBAC, and user lifecycle management — all directly relevant to the Microsoft SC-500 identity and access management domain.

## Prerequisites

- `keycloak-server` VM running Ubuntu 22.04 (cloned in Guide 01)
- Static IP set to `192.168.56.11`
- At least 2 GB RAM allocated to this VM

```bash
VBoxManage modifyvm "keycloak-server" --memory 2048 --cpus 1
```

## Install Dependencies

SSH into the Keycloak server:

```bash
ssh labadmin@192.168.56.11
```

### Install Java (Keycloak requires JDK 17+)

```bash
sudo apt update
sudo apt install -y openjdk-17-jdk

java --version
# Should show OpenJDK 17.x
```

### Install PostgreSQL

Keycloak supports multiple databases. PostgreSQL is production-grade and worth using even in a lab for realistic experience:

```bash
sudo apt install -y postgresql postgresql-contrib

# Start and enable
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

Create the Keycloak database and user:

```bash
sudo -u postgres psql << 'SQL'
CREATE DATABASE keycloak;
CREATE USER keycloak WITH PASSWORD 'KeycloakLabDB2024!';
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
ALTER DATABASE keycloak OWNER TO keycloak;
SQL
```

## Install Keycloak

```bash
# Download Keycloak (check https://www.keycloak.org/downloads for current version)
cd /opt
sudo wget https://github.com/keycloak/keycloak/releases/download/25.0.0/keycloak-25.0.0.tar.gz
sudo tar -xzf keycloak-25.0.0.tar.gz
sudo mv keycloak-25.0.0 keycloak
sudo chown -R labadmin:labadmin /opt/keycloak
```

### Configure Keycloak

Edit the Keycloak configuration to use PostgreSQL and bind to the lab network:

```bash
nano /opt/keycloak/conf/keycloak.conf
```

Add or modify these settings:

```properties
# Database
db=postgres
db-url-host=localhost
db-url-database=keycloak
db-username=keycloak
db-password=KeycloakLabDB2024!

# Network — bind to lab IP
hostname=keycloak.lab.local
http-enabled=true
http-port=8080
http-host=0.0.0.0

# For lab use: allow HTTP (production would require HTTPS)
hostname-strict=false
hostname-strict-https=false
```

### Build and Start Keycloak

```bash
# Build optimized runtime
/opt/keycloak/bin/kc.sh build

# Start in development mode for initial setup
/opt/keycloak/bin/kc.sh start-dev &
```

### Create the Admin User

On first run, create the initial admin:

```bash
# Set admin credentials via environment variables
export KEYCLOAK_ADMIN=admin
export KEYCLOAK_ADMIN_PASSWORD='KcAdmin2024!'

# Restart to pick up the admin user
/opt/keycloak/bin/kc.sh start-dev
```

Access the admin console at `http://192.168.56.11:8080` from the host browser.

### Create a systemd Service

For persistent operation, create a service file:

```bash
sudo tee /etc/systemd/system/keycloak.service << 'EOF'
[Unit]
Description=Keycloak Identity Provider
After=network.target postgresql.service

[Service]
Type=simple
User=labadmin
Environment=KEYCLOAK_ADMIN=admin
Environment=KEYCLOAK_ADMIN_PASSWORD=KcAdmin2024!
ExecStart=/opt/keycloak/bin/kc.sh start-dev
ExecStop=/bin/kill -SIGTERM $MAINPID
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable keycloak
sudo systemctl start keycloak
```

## Lab Realm Configuration

Instead of using the default `master` realm, create a dedicated lab realm that mirrors an enterprise environment.

### Step 1 — Create the Security Lab Realm

1. Log into the Keycloak Admin Console at `http://192.168.56.11:8080`
2. Click the realm dropdown (top-left, says "master") → **Create Realm**
3. Set Realm name: `security-lab`
4. Enable it and save

### Step 2 — Define Roles (RBAC)

Create roles that map to a realistic security operations team:

Navigate to **Realm roles → Create role** and add:

| Role | Description | SC-500 Mapping |
|---|---|---|
| `soc-analyst-t1` | Tier 1 analyst — alert triage, read-only dashboards | Security Reader |
| `soc-analyst-t2` | Tier 2 analyst — investigation, rule tuning | Security Operator |
| `security-engineer` | Full SIEM admin, detection engineering | Security Administrator |
| `iam-admin` | Identity and access management operations | Privileged Role Administrator |
| `auditor` | Read-only access for compliance review | Compliance Reader |

### Step 3 — Create Lab Users

Navigate to **Users → Add user** and create:

| Username | Role | Purpose |
|---|---|---|
| `analyst.t1` | `soc-analyst-t1` | Practice alert triage with limited permissions |
| `analyst.t2` | `soc-analyst-t2` | Practice investigation workflows |
| `sec.engineer` | `security-engineer` | Full admin for detection rule authoring |
| `iam.admin` | `iam-admin` | Practice user lifecycle management |
| `auditor` | `auditor` | Practice access reviews |

For each user:
1. Set a temporary password in the **Credentials** tab
2. Toggle **Temporary** to ON (forces password change on first login)
3. Assign the role in the **Role Mappings** tab

### Step 4 — Enable MFA

Configure OTP-based MFA for the realm:

1. Navigate to **Authentication → Flows → Browser**
2. The default browser flow includes "OTP Form" as optional
3. Click on the OTP Form requirement and set it to **Required**
4. Under **Realm Settings → Login**, enable **OTP Policy**

Configure OTP settings:
1. Go to **Authentication → Policies → OTP Policy**
2. Set algorithm to **SHA-256** (or SHA-1 for broader authenticator compatibility)
3. Set digits to **6**
4. Set period to **30 seconds**

Users will be prompted to set up an authenticator app (Google Authenticator, Authy, etc.) on their next login.

### Step 5 — Configure SSO Client (OIDC)

Register Wazuh as an OIDC client so analysts log into the Wazuh Dashboard through Keycloak:

1. Navigate to **Clients → Create client**
2. Set:
   - Client ID: `wazuh-dashboard`
   - Client Protocol: `openid-connect`
   - Root URL: `https://192.168.56.10`
3. In the client settings:
   - Access Type: `confidential`
   - Valid Redirect URIs: `https://192.168.56.10/*`
   - Web Origins: `https://192.168.56.10`
4. Save and note the **Client Secret** from the Credentials tab

> **Integration with Wazuh Dashboard:** Wazuh Dashboard (OpenSearch Dashboards) supports OIDC. The configuration details are covered in the [Wazuh OIDC documentation](https://documentation.wazuh.com/current/user-manual/user-administration/single-sign-on/). This connects your RBAC roles to actual dashboard permissions.

### Step 6 — Export the Realm Configuration

Export your realm config so it's version-controlled and reproducible:

```bash
/opt/keycloak/bin/kc.sh export \
  --dir /tmp/keycloak-export \
  --realm security-lab \
  --users realm_file
```

Copy the export to the repo:

```bash
cp /tmp/keycloak-export/security-lab-realm.json \
  ~/Security-Operations-Lab/configs/keycloak/
```

## User Lifecycle Exercises

These exercises build demonstrable IAM experience for your portfolio:

### Exercise 1 — Onboarding
Provision a new analyst (`new.analyst`), assign `soc-analyst-t1`, enforce MFA, verify they can access Wazuh Dashboard with read-only permissions.

### Exercise 2 — Role Change
Promote `analyst.t1` to `soc-analyst-t2`. Verify expanded permissions take effect immediately via Wazuh Dashboard.

### Exercise 3 — Access Review
Generate a list of all users and their roles. Identify any over-privileged accounts. Document findings in a mock access review report.

### Exercise 4 — Offboarding
Disable `new.analyst` account. Verify all sessions are terminated and access is revoked. Document the offboarding checklist.

## Snapshot

```bash
VBoxManage snapshot "keycloak-server" take "keycloak-configured" \
  --description "Keycloak installed, security-lab realm with RBAC roles, MFA enabled, OIDC client for Wazuh"
```

## What You've Built

- Keycloak identity provider with a realistic security operations realm
- RBAC roles mapping to SC-500 identity concepts
- MFA enforcement via OTP
- OIDC client configuration for SSO with Wazuh Dashboard
- User lifecycle management workflows
- Version-controlled realm export for reproducibility

## Next Step

Proceed to [05 — OpenDLP Configuration](05-opendlp-setup.md) to set up data discovery and classification.
