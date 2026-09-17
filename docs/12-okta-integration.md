# 12 — Okta Developer Integration

This guide sets up a free Okta developer tenant as an enterprise-grade identity provider alongside your local Keycloak and Active Directory. Okta appears on a huge number of job postings, so hands-on experience with the admin console, SSO configuration, and MFA policies is directly resume-relevant.

## What You Get (Free, No Billing)

The Okta Developer account at [developer.okta.com](https://developer.okta.com/signup/) includes:

- Full Okta admin console
- Up to 100 users (more than enough for lab work)
- OIDC and SAML SSO
- MFA with Okta Verify, Google Authenticator, SMS
- User provisioning and lifecycle management
- API access for automation
- No credit card required, no expiration

## Create the Okta Developer Account

1. Go to [developer.okta.com/signup](https://developer.okta.com/signup/)
2. Sign up with your email
3. You'll receive an Okta org URL like `https://dev-12345678.okta.com`
4. Log in to the Admin Console

Save your Okta org URL — you'll reference it throughout this guide.

## Configure the Okta Tenant

### Step 1 — Create Users That Mirror Your AD Domain

In the Okta Admin Console, go to **Directory → People → Add Person**:

| First Name | Last Name | Username | Group |
|---|---|---|---|
| SOC | Analyst-T1 | soc.t1@dev-XXXXX.okta.com | SOC-Tier1 |
| SOC | Analyst-T2 | soc.t2@dev-XXXXX.okta.com | SOC-Tier2 |
| Security | Engineer | sec.engineer@dev-XXXXX.okta.com | SecurityEngineers |
| IAM | Admin | iam.admin@dev-XXXXX.okta.com | IAMAdmins |

### Step 2 — Create Groups for RBAC

Go to **Directory → Groups → Add Group**:

- `SOC-Tier1` — read-only SIEM access
- `SOC-Tier2` — investigation and response access
- `SecurityEngineers` — full admin access
- `IAMAdmins` — identity management access

Assign users to their groups.

### Step 3 — Enable MFA

Go to **Security → Multifactor → Factor Enrollment**:

1. Enable **Okta Verify** (push notifications)
2. Enable **Google Authenticator** (TOTP)
3. Set enrollment policy to **Required** for all users
4. Under **Authentication Policies**, create a policy that requires MFA for all app access

### Step 4 — Register Wazuh Dashboard as a SAML App

This lets analysts sign into Wazuh using their Okta credentials:

1. Go to **Applications → Create App Integration**
2. Select **SAML 2.0**
3. App name: `Wazuh Dashboard`
4. Configure SAML settings:
   - Single Sign-On URL: `https://192.168.56.10/_opendistro/_security/saml/acs`
   - Audience URI (SP Entity ID): `https://192.168.56.10`
   - Name ID format: `EmailAddress`
5. Attribute statements:
   - `roles` → `user.groups` (maps Okta groups to Wazuh roles)
6. Download the **IdP Metadata XML** — you'll need this for Wazuh configuration

Assign the app to the relevant groups (SOC-Tier1, SOC-Tier2, SecurityEngineers).

### Step 5 — Register Keycloak as an OIDC App (Federation)

This demonstrates IdP federation — a key enterprise IAM pattern:

1. **Applications → Create App Integration → OIDC - Web Application**
2. App name: `Keycloak Federation`
3. Sign-in redirect URI: `http://192.168.56.11:8080/realms/security-lab/broker/okta/endpoint`
4. Sign-out redirect URI: `http://192.168.56.11:8080/realms/security-lab`
5. Assignments: assign to all groups
6. Note the **Client ID** and **Client Secret**

Then in Keycloak (Guide 04):
1. Go to **Identity Providers → Add Provider → OpenID Connect v1.0**
2. Alias: `okta`
3. Authorization URL: `https://dev-XXXXX.okta.com/oauth2/v1/authorize`
4. Token URL: `https://dev-XXXXX.okta.com/oauth2/v1/token`
5. Client ID / Secret: from the Okta app above

This creates a "Login with Okta" option on your Keycloak login page — exactly how enterprises federate cloud and on-prem identity.

## Okta API Automation with Python

Create a script that demonstrates programmatic user lifecycle management:

```python
#!/usr/bin/env python3
"""
Okta User Lifecycle — Demonstrate provisioning, access review, and offboarding via API.
Requires: pip install okta
"""

import json
from okta.client import Client as OktaClient

# Configure — set these from environment variables in practice
OKTA_ORG_URL = "https://dev-XXXXX.okta.com"
OKTA_API_TOKEN = "YOUR_API_TOKEN"  # Create in Security → API → Tokens

config = {
    'orgUrl': OKTA_ORG_URL,
    'token': OKTA_API_TOKEN
}

async def provision_user(client):
    """Onboarding: create a new user and assign to a group."""
    user_profile = {
        'firstName': 'New',
        'lastName': 'Analyst',
        'email': 'new.analyst@lab.local',
        'login': 'new.analyst@lab.local',
    }
    body = {
        'profile': user_profile,
        'credentials': {
            'password': {'value': 'TempP@ss123!'}
        }
    }
    user, resp, err = await client.create_user(body, activate=True)
    if err:
        print(f"Error creating user: {err}")
        return None
    print(f"Created user: {user.profile.login} (ID: {user.id})")
    return user

async def access_review(client):
    """List all users and their group memberships for access review."""
    users, resp, err = await client.list_users()
    if err:
        print(f"Error: {err}")
        return

    print("\n=== ACCESS REVIEW REPORT ===")
    for user in users:
        groups, _, _ = await client.list_user_groups(user.id)
        group_names = [g.profile.name for g in groups] if groups else []
        status = user.status
        print(f"  {user.profile.login:30s} Status: {status:10s} Groups: {', '.join(group_names)}")

async def offboard_user(client, login):
    """Offboarding: deactivate and suspend a user."""
    users, _, err = await client.list_users({'search': f'profile.login eq "{login}"'})
    if err or not users:
        print(f"User not found: {login}")
        return

    user = users[0]
    # Deactivate (revokes all sessions and app access)
    await client.deactivate_user(user.id)
    print(f"Deactivated: {user.profile.login}")

# Run with: asyncio.run(main())
```

Save this to `scripts/analysis/okta_lifecycle.py`.

## Portfolio Exercises

### Exercise 1 — SSO Login Flow
Log into Wazuh Dashboard using Okta credentials. Screenshot the SAML flow, the Okta MFA prompt, and the successful Wazuh landing page. Document the entire SSO chain.

### Exercise 2 — Federated Login via Keycloak
Log into Keycloak using the "Login with Okta" button. Document how the user is created in Keycloak via Just-In-Time (JIT) provisioning from Okta.

### Exercise 3 — Access Review Report
Run the Python access review script, generate a report of all users and their group memberships, identify any over-privileged accounts, document remediation.

### Exercise 4 — Okta vs AD vs Keycloak Comparison
Write a one-page comparison of the three identity platforms in your lab — what each does well, where you'd use each in an enterprise, how they federate. This shows depth of understanding beyond just "I can click through a GUI."

## Configs to Version Control

Export and save to the repo:

```bash
mkdir -p configs/okta
# Save SAML metadata, app configurations, and MFA policy screenshots
# Do NOT commit API tokens — add them to .gitignore
```

Add to `.gitignore`:

```
configs/okta/*token*
configs/okta/*secret*
```

## Next Step

Proceed to [13 — AWS Free Tier Security Lab](13-aws-free-tier.md) to extend the lab into cloud security.
