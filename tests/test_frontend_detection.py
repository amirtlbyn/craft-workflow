import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import craft_stack
from frontend.build.detection import detect as detect_build
from frontend.stacks.detection import detect as detect_frontend


def project(tmp_path, files):
    (tmp_path / ".git").mkdir(exist_ok=True)
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path


def test_framework_detector_reports_framework_and_build_tool(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"dependencies": {"react": "19"}}), "vite.config.ts": "export default {}"})
    result = detect_frontend(root)
    assert [(item.framework, item.build_tools) for item in result] == [("react", ("vite",))]


def test_detector_handles_malformed_manifest(tmp_path):
    assert detect_frontend(project(tmp_path, {"package.json": "{"})) == []


def test_craft_stack_prefers_frontend_pack_over_node(tmp_path):
    project(tmp_path, {"package.json": json.dumps({"dependencies": {"vue": "3"}})})
    found = craft_stack.detect(str(tmp_path))
    assert [item["id"] for item in found] == ["vue"]


def test_build_detection_uses_config_and_package_evidence(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"devDependencies": {"webpack": "5"}})})
    assert [(item.name, item.config) for item in detect_build(root)] == [("webpack", "")]


def test_nuxt_project_reports_nuxt_framework(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0", "vue": "^3.5.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    result = detect_frontend(root)
    assert [(item.framework, item.build_tools) for item in result] == [("nuxt", ("nuxt",))]


def test_nuxt_without_vue_dep_still_detected(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}})})
    assert [item.framework for item in detect_frontend(root)] == ["nuxt"]


def test_build_detection_reports_nuxt_config(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    assert [(item.name, item.config) for item in detect_build(root)] == [("nuxt", "nuxt.config.ts")]


def test_build_detection_reports_nuxt_dependency_without_config(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}})})
    assert [(item.name, item.config) for item in detect_build(root)] == [("nuxt", "")]


def test_craft_stack_prefers_nuxt_pack_over_vue(tmp_path):
    project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    found = craft_stack.detect(str(tmp_path))
    assert [item["id"] for item in found] == ["nuxt"]


def test_craft_stack_lens_resolves_nuxt_sections_by_name(tmp_path):
    project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}}),
        "nuxt.config.ts": "export default defineNuxtConfig({})",
    })
    for lens in ("ssr", "data", "hydration", "component", "accessibility"):
        assert len(craft_stack.lens_addendum(lens, "nuxt")) > 40, lens


def test_skills_for_omits_skills_without_files(tmp_path, monkeypatch):
    project(tmp_path, {"package.json": json.dumps({"dependencies": {"nuxt": "^4.0.0"}})})
    monkeypatch.setattr(craft_stack, "detect", lambda cwd=None: [{"id": "nuxt", "dir": "", "evidence": "x"}])
    skills = craft_stack.skills_for(cwd=str(tmp_path), with_concurrency=False)
    assert skills, "expected the nuxt pack to list skills"
    for name in skills:
        assert (craft_stack.PLUGIN_ROOT / "skills" / name / "SKILL.md").exists(), name


def test_angular_project_detected(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"dependencies": {"@angular/core": "^18.0.0"}})})
    assert [item.framework for item in detect_frontend(root)] == ["angular"]


def test_react_next_build_tool_detected(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"react": "^19.0.0", "next": "^15.0.0"}}),
        "next.config.mjs": "export default {}",
    })
    assert [(item.framework, item.build_tools) for item in detect_frontend(root)] == [("react", ("next",))]


def test_react_remix_build_tool_detected(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"react": "^18.0.0", "@remix-run/node": "^2.0.0"}}),
        "remix.config.js": "export default {}",
    })
    assert [(item.framework, item.build_tools) for item in detect_frontend(root)] == [("react", ("remix",))]


def test_vue_cli_build_tool_detected(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"vue": "^3.0.0", "@vue/cli-service": "^5.0.0"}}),
        "vue.config.js": "export default {}",
    })
    assert [(item.framework, item.build_tools) for item in detect_frontend(root)] == [("vue", ("vue-cli",))]


def test_first_level_workspaces_detected(tmp_path):
    root = project(tmp_path, {
        "web/package.json": json.dumps({"dependencies": {"vue": "^3.0.0"}}),
        "api/package.json": json.dumps({"dependencies": {"react": "^19.0.0"}}),
    })
    assert sorted(item.framework for item in detect_frontend(root)) == ["react", "vue"]


def test_second_level_directories_out_of_scope(tmp_path):
    root = project(tmp_path, {"a/b/package.json": json.dumps({"dependencies": {"vue": "^3.0.0"}})})
    assert detect_frontend(root) == []
