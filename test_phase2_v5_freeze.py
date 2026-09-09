import subprocess

# Phase 2 must not alter the frozen V5 intelligence implementation.
FROZEN_FILES = [
    "anvi_knowledge_layer.py",
    "anviqo_product.py",
    "plant_brain_reasoning.py",
    "plant_condition_synthesizer.py",
]


def test_v5_frozen_files_unchanged():
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "origin/main...HEAD", "--", *FROZEN_FILES],
        text=True,
    ).splitlines()
    assert changed == [], f"Frozen V5 files changed in Phase 2: {changed}"


if __name__ == "__main__":
    test_v5_frozen_files_unchanged()
    print("V5 FROZEN FILE CHECK: PASS")
