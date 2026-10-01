from pathlib import Path

def test_mobile_command_centre():
    html=Path("anviqo_dashboard.html").read_text(encoding="utf-8")
    for page,label in [("overview","Home"),("alarms","Alarms"),("ask","ANVI"),("critical","Equipment"),("safety","Safety")]:
        assert f'data-mobile-page="{page}"' in html
        assert f'<small>{label}</small>' in html
    assert "V2 MOBILE COMMAND CENTRE" in html
    assert "no second intelligence layer" in html
