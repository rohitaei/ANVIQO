# ANVIQO Universal Approved Data Ingestion V1

## Purpose
Connect plant-supplied data to `ANVIQO-ONBOARDING-V1` through a connector-neutral boundary.

## Principle
**CHANGE DATA, NOT CODE.**

The ingestion layer accepts approved source adapters and normalizes their records through the existing onboarding contract. The V5 intelligence layer remains unchanged and is the consumer.

## V1 sources
- JSON package with embedded plant identity
- CSV records with configured plant identity
- Connector-neutral in-memory records for future vendor/API adapters

The source is recorded with a SHA-256 fingerprint when a file is supplied.

## Safety
- Read-only intelligence: true
- PLC write: false
- SCADA control: false
- Automatic authorization: false
- Automatic execution: false
- Human decision required: true

This layer validates/transports data only. It does not connect to or command PLC/SCADA systems and does not create predictions or diagnoses.

## Acceptance gate
A second plant dataset must be loadable through the same `ingest_file()` / `ingest_records()` interface, producing the same onboarding contract while changing only plant data/configuration.

Implementation: `universal_data_ingestion.py`
Test: `test_universal_data_ingestion.py`
