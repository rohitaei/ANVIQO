"""Compatibility entry point for the V1.4 universal tenant chat engine.

The implementation lives in anvi_chat_stability_v2.  This stable module name
is retained because the universal engine and existing integrations import it.
No importer, PCI or V5 files are modified here.
"""
from anvi_chat_stability_v2 import (
    install,
    _query_rows,
    _exact_answer,
    _summary_answer,
)

__all__ = ["install", "_query_rows", "_exact_answer", "_summary_answer"]
