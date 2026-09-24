# Acme Logistics: Data Retention and Security Standard (Engineering Internal)

Owner: Platform Engineering and Security. Version 2.2. Internal: Engineering staff only.

## Retention periods

| Data type | Retention |
|-----------|-----------|
| Vehicle telemetry | **13 months** |
| Dispatch logs | **24 months** |
| Audit logs | **3 years**, stored immutably |
| Customer personal data | **7 years** after the contract ends |

Customer personal data must be deleted within **30 days** after the 7-year period ends. Customer deletion requests that are legally valid must also be completed within **30 days**.

## Backups

Daily backups are kept for **35 days**. Monthly backups are kept for **12 months**. Backups are stored in a different region from the primary database, and restore tests run quarterly.

## Encryption

All databases and backups are encrypted at rest with **AES-256**. All traffic between services uses TLS 1.2 or higher. Encryption keys rotate every 12 months.

## Access control

Production access follows least privilege. Access reviews happen **quarterly**, and any access not re-approved by its owner is removed automatically. Engineers must use a company-managed device and hardware security key to reach production.

## Deployment freeze

There is a code freeze on production deployments from **November 15 through January 5** to protect peak-season stability. Emergency fixes during the freeze need Engineering Director approval.

## Reporting a security issue

Report suspected data exposure to security@acmelogistics.com immediately. The Security team acknowledges reports within 1 hour.
