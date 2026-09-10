def test_replacement_sentence_extracts_new_spare_used():
    import sitecustomize  # noqa: F401 - installs the compatibility hook
    from anvi_field_report import parse_field_report

    report = parse_field_report(
        "Pt304 was faulty checked and replaced by new pt-303 1 no spare used now it is ok"
    )

    assert report["spare_used"] == "PT-303 x1"


def test_replacement_sentence_keeps_report_pending_verification():
    import sitecustomize  # noqa: F401
    from anvi_field_report import parse_field_report

    report = parse_field_report(
        "Pt304 was faulty checked and replaced by new pt-303 1 no spare used now it is ok"
    )

    assert report.get("verification_status", "PENDING_VERIFICATION") == "PENDING_VERIFICATION"
