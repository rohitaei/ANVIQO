"""Durable, low-memory tenant plant ingestion adapter.

This is data ingestion only. Existing V5 intelligence and PLC/SCADA safety
boundaries are untouched. CHANGE DATA, NOT CODE.

Recovery note: stale RUNNING jobs must be surfaced as STALE so the UI can
safely allow a fresh ingestion after a worker interruption.
"""
