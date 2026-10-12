from anviqo_api import _extract_v3_tag


def test_v3_tag_extraction_handles_common_separators():
    assert _extract_v3_tag("Is PT-303 getting worse?") == "PT_303"
    assert _extract_v3_tag("Show PT_303 instrument health") == "PT_303"
    assert _extract_v3_tag("Give an early warning for FT 519") == "FT_519"
    assert _extract_v3_tag("Show plant health") is None
