"""Tests that the bundled agent skill is well formed."""

import re
import subprocess
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1] / "skills" / "room-snapshot"
SKILL = SKILL_DIR / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text():
    return SKILL.read_text(encoding="utf-8")


def test_frontmatter_has_name_and_description(skill_text):
    assert skill_text.startswith("---\n")
    front = skill_text.split("---", 2)[1]
    assert re.search(r"^name: room-snapshot$", front, re.MULTILINE)
    description = re.search(r"^description: >-\n((?:  .*\n)+)", front, re.MULTILINE)
    assert description, "description must be a folded block"
    text = " ".join(line.strip() for line in description.group(1).splitlines())
    assert len(text) > 40


def test_referenced_files_exist(skill_text):
    references = set(re.findall(r"`(references/[a-z-]+\.md)`", skill_text))
    assert references
    for reference in references:
        assert (SKILL_DIR / reference).is_file(), reference


def test_scripts_are_valid_shell():
    scripts = sorted((SKILL_DIR / "scripts").glob("*.sh"))
    assert scripts
    for script in scripts:
        subprocess.run(["sh", "-n", str(script)], check=True)


def test_skill_is_english(skill_text):
    assert not re.search(r"[А-Яа-яЁё]", skill_text)
