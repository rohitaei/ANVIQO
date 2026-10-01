from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]

def test_create_plant_initializes_onboarding():
    src = (ROOT / "anvi_plant_auth_routes.py").read_text(encoding="utf-8")
    assert "universal_onboarding.ensure_plant(plant_id)" in src
    assert '"onboarding_status": "CREATED"' in src

def test_create_plant_validates_slug_and_duplicate():
    src = (ROOT / "anvi_plant_auth_routes.py").read_text(encoding="utf-8")
    assert 're.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)' in src
    assert '"CONFLICT"' in src
    ast.parse(src)

def test_onboarding_uses_current_import_contract():
    src = (ROOT / "anvi_plant_data_upload.html").read_text(encoding="utf-8")
    assert "/api/admin/onboarding/plant/'+encodeURIComponent(id)+'/import" in src
    assert "/api/admin/onboarding/plant/'+encodeURIComponent(id)+'/import-status" in src
    assert "/api/admin/onboarding/plant/'+encodeURIComponent(id)+'/knowledge-summary" in src

def test_plant_admin_offers_created_plant_onboarding():
    src = (ROOT / "plant_user_admin.html").read_text(encoding="utf-8")
    assert "/admin/onboarding?plant=" in src
