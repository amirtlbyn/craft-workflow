import json
import pathlib

from frontend.build.analyzer import (
    analyze_assets,
    analyze_bundle,
    analyze_performance,
    analyze_splitting,
    analyze_tree_shaking,
)
from frontend.build.detection import detect as detect_build

sys_path = pathlib.Path(__file__).resolve().parent.parent


def project(tmp_path, files):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    return tmp_path


def test_build_detection_uses_config_and_package_evidence(tmp_path):
    root = project(tmp_path, {"package.json": json.dumps({"devDependencies": {"webpack": "5"}})})
    assert [(item.name, item.config) for item in detect_build(root)] == [("webpack", "")]


def test_bundle_report_counts_files_and_dependencies(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"react": "19"}, "devDependencies": {"vite": "6"}}),
        "src/index.js": "console.log('hi');\n" * 10,
    })
    report = analyze_bundle(root)
    assert report.file_count == 1
    assert report.total_source_bytes > 0
    assert report.dependency_count == 2
    assert report.verdict == "ok"


def test_bundle_report_flags_oversized_tree(tmp_path):
    root = project(tmp_path, {"src/blob.js": "x = 1;\n" * 200_000})
    assert analyze_bundle(root).verdict in ("warning", "error")


def test_assets_over_budget_flagged(tmp_path):
    root = project(tmp_path, {
        "public/hero.png": b"\x89PNG" + b"0" * 300_000,
        "public/icon.svg": b"<svg></svg>",
    })
    assert [issue.path for issue in analyze_assets(root)] == ["public/hero.png"]


def test_splitting_detects_lazy_loading(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"react": "19"}}),
        "src/App.tsx": "const Page = React.lazy(() => import('./Page'));\n",
        "src/Page.tsx": "export default () => null;\n",
    })
    assert analyze_splitting(root).lazy_count == 1


def test_splitting_suggests_for_eager_routes(tmp_path):
    root = project(tmp_path, {
        "src/pages/one.ts": "export default 1;\n",
        "src/pages/two.ts": "export default 2;\n",
        "src/pages/three.ts": "export default 3;\n",
        "src/pages/four.ts": "export default 4;\n",
    })
    assert analyze_splitting(root).unsplit_routes != ()


def test_splitting_does_not_flag_framework_routers(tmp_path):
    root = project(tmp_path, {
        "nuxt.config.ts": "export default defineNuxtConfig({});",
        "pages/a.vue": "<template><div/></template>",
        "pages/b.vue": "<template><div/></template>",
        "pages/c.vue": "<template><div/></template>",
        "pages/d.vue": "<template><div/></template>",
    })
    assert analyze_splitting(root).unsplit_routes == ()


def test_tree_shaking_finds_unused_dependency(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"lodash": "4", "dayjs": "1"}, "devDependencies": {"eslint": "9"}}),
        "src/index.js": "import dayjs from 'dayjs';\nrequire('eslint');\n",
    })
    unused = analyze_tree_shaking(root)
    assert [item.name for item in unused] == ["lodash"]


def test_tree_shaking_handles_scoped_packages(tmp_path):
    root = project(tmp_path, {
        "package.json": json.dumps({"dependencies": {"@vueuse/core": "11", "vue": "3"}}),
        "src/index.js": "import { useStorage } from '@vueuse/core';\nimport { createApp } from 'vue';\n",
    })
    assert analyze_tree_shaking(root) == []


def test_performance_counts_static_risks(tmp_path):
    root = project(tmp_path, {
        "app.html": '<html><head><link rel="stylesheet" href="a.css"></head>'
                    '<body><script src="app.js"></script><img src="hero.png"></body></html>',
        "src/vitals.js": "import { getCLS, getLCP } from 'web-vitals';\n",
    })
    report = analyze_performance(root)
    assert report.render_blocking == 1
    assert report.synchronous_scripts == 1
    assert report.unstyled_images == 1
    assert report.vitals_instrumented is True


def test_performance_reports_missing_vitals(tmp_path):
    root = project(tmp_path, {"index.html": "<p>hi</p>"})
    report = analyze_performance(root)
    assert report.vitals_instrumented is False
    assert any("web-vitals" in finding for finding in report.findings)
