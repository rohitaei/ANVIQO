# ANVIQO Global V2 Safety & Security Contract

This document is mandatory for every V2 module.

## Control boundary
- Read-only by default.
- No automatic PLC write.
- No automatic SCADA control.
- No automatic authorization.
- No automatic execution.
- Human decision required.

## Tenant boundary
Every evidence query must carry authenticated organization_id and plant_id.
Foreign-plant evidence is never a fallback.
Legacy evidence without explicit ownership is treated as untrusted for universal tenant use.

## Edge boundary
Plant OT is never exposed directly to the public internet.
The intended path is:
PLC/DCS -> plant LAN -> read-only gateway -> outbound TLS -> cloud.

## Security requirements
- Strong identity and role separation.
- MFA/SSO for enterprise deployments.
- Encryption in transit and at rest.
- Secrets outside source code.
- Immutable audit trail for safety/authorization decisions.
- Connector credentials isolated per plant.
- Network segmentation.
- Rate limiting and abuse protection.
- Backup and recovery testing.
- Security and dependency scanning.

## AI governance
Every high-impact recommendation must retain:
intent, evidence, context, reasoning basis, confidence, safety status and human decision state.
ANVI must not claim causation when evidence only establishes correlation.
