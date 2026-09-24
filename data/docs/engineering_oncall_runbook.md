# Acme Logistics: On-Call and Incident Runbook (Engineering Internal)

Owner: Platform Engineering. Version 3.4. Internal: Engineering staff only.

## On-call rotation

On-call runs weekly. The handoff happens every **Monday at 10:00 AM Central Time**. Each rotation has a primary and a secondary engineer. On-call engineers receive a stipend of **$600 per week**. Paging is handled through PagerDuty.

## Severity levels

| Severity | Definition | Acknowledge within |
|----------|------------|--------------------|
| SEV1 | Full outage of the dispatch platform | **10 minutes** |
| SEV2 | Major feature degraded, workaround exists | **30 minutes** |
| SEV3 | Minor issue, no customer impact | Next business day |

SEV1 incidents page the primary engineer immediately, 24 hours a day.

## Escalation

If the primary engineer does not acknowledge a page within **15 minutes**, PagerDuty escalates to the secondary. If the secondary does not acknowledge within a further 15 minutes, it escalates to the **Engineering Director**.

## Running a SEV1

1. The first responder declares the incident and opens the bridge line.
2. The Engineering Director (or a delegate) becomes **Incident Commander**.
3. Post a status update every **30 minutes** until the incident is resolved.
4. Do not deploy unrelated changes while a SEV1 is open.

## After the incident

A written postmortem is due within **5 business days** of resolution. Postmortems are blameless and must list a root cause, a timeline, and at least one preventive action with an owner.

## Escalation contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Engineering Director | Sofia Reyes | (901) 555-0181 | sofia.reyes@acmelogistics.com |
| Primary on-call (this month) | Kenji Watanabe | (901) 555-0152 | kenji.watanabe@acmelogistics.com |
| Secondary on-call (this month) | Amara Nwosu | (901) 555-0139 | amara.nwosu@acmelogistics.com |
