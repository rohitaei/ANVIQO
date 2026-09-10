# ANVIQO Universal Industrial Onboarding V1

## Purpose

Create a stable plant-data contract for deploying ANVIQO to different industrial plants without modifying the frozen V5 intelligence.

## Acceptance principle

**CHANGE DATA, NOT CODE.**

A new plant supplies/configures its identity and records; the existing ANVIQO intelligence remains the consumer.

## Supported normalized concepts

- Plant identity: organization, plant, name, industry, timezone
- Assets/equipment
- Instruments/tags
- Areas/units/locations
- Services/process context
- Parent/child relationships
- Source documents/data provenance
- Extensible metadata

Common source column names are normalized at the adapter boundary (for example `asset_id`/`id`/`tag` → `external_id`). No V5 reasoning logic is duplicated.

## Safety

- read-only intelligence: true
- PLC write: false
- SCADA control: false
- automatic authorization: false
- automatic execution: false
- human decision required: true

The onboarding adapter validates and normalizes supplied data only. It does not operate plant equipment or fabricate plant intelligence.

## Contract

`ANVIQO-ONBOARDING-V1`

Implementation: `universal_onboarding.py`

## Next integration gate

Connect approved plant-data ingestion sources to this contract, then prove that the same existing intelligence APIs can consume a second plant dataset without core-code changes. Integration must be additive and must preserve the V5 freeze and tenant isolation.
