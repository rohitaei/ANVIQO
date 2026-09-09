import failure_prediction_dashboard_runtime as runtime


def test_dashboard_injects_explicit_demo_panel_only_once():
    html = '<html><body><div id="page-prediction"><div id="predictionData"></div></div></body></html>'
    updated = runtime.inject_prediction_demo_dashboard(html)
    assert 'id="anviqoFpDemo"' in updated
    assert '/api/failure_prediction/demo' in updated
    assert 'DEMO / SYNTHETIC DATA' in updated
    assert 'PLC / SCADA control' in updated
    assert 'Human decision' in updated
    assert runtime.inject_prediction_demo_dashboard(updated) == updated


def test_dashboard_injection_does_not_touch_unrelated_html():
    html = '<html><body><div id="page-overview"></div></body></html>'
    assert runtime.inject_prediction_demo_dashboard(html) == html
