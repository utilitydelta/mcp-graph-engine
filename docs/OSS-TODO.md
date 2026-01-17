# Open Source Release Checklist

Everything that needs doing before this repo is ready for public consumption.

---

## 1. Legal and Licensing

### 1.1 Add LICENSE file
**Priority: BLOCKER**

Create `LICENSE` in repo root. MIT is standard for this kind of tool.

```
MIT License

Copyright (c) 2025 utilitydelta

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 1.2 Dependency license audit
**Priority: High**

Verify all dependencies are compatible with MIT:
- [ ] networkx (BSD-3-Clause) - OK
- [ ] mcp (check license)
- [ ] sentence-transformers (Apache-2.0) - OK
- [ ] grand-cypher (Apache-2.0) - OK
- [ ] fastapi (MIT) - OK
- [ ] uvicorn (BSD-3-Clause) - OK
- [ ] pydot (MIT) - OK
- [ ] websockets (BSD-3-Clause) - OK

---

## 2. Package Metadata

### 2.1 Complete pyproject.toml
**Priority: BLOCKER**

Current `pyproject.toml` is missing critical fields. Update to:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mcp-graph-engine"
version = "0.1.0"
description = "A graph database and analysis tool for AI assistants via MCP"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.10"
authors = [
    {name = "utilitydelta", email = "your-email@example.com"}
]
maintainers = [
    {name = "utilitydelta", email = "your-email@example.com"}
]
keywords = [
    "mcp",
    "graph",
    "knowledge-graph",
    "llm",
    "ai-assistant",
    "networkx",
    "cypher",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "Topic :: Database :: Database Engines/Servers",
]

[project.urls]
Homepage = "https://github.com/utilitydelta/mcp-graph-engine"
Documentation = "https://github.com/utilitydelta/mcp-graph-engine#readme"
Repository = "https://github.com/utilitydelta/mcp-graph-engine.git"
Issues = "https://github.com/utilitydelta/mcp-graph-engine/issues"
Changelog = "https://github.com/utilitydelta/mcp-graph-engine/blob/main/CHANGELOG.md"

# ... rest of existing config
```

---

## 3. Documentation Assets

### 3.1 Create docs/assets directory
**Priority: High**

```bash
mkdir -p docs/assets
```

### 3.2 Record demo GIFs
**Priority: High**

Use a tool like [Peek](https://github.com/phw/peek), [LICEcap](https://www.cockos.com/licecap/), or [asciinema](https://asciinema.org/) + [svg-term-cli](https://github.com/marionebl/svg-term-cli).

| Asset | Description | Suggested dimensions |
|-------|-------------|---------------------|
| `docs/assets/hero.gif` | Main demo: Claude adding nodes while D3 viz updates live | 800x500, <5MB |
| `docs/assets/realtime-updates.gif` | Close-up of graph updating as nodes are added | 600x400, <3MB |
| `docs/assets/cycles.png` | Screenshot showing detected cycle in visualisation | 800x500 |

**Recording checklist:**
- [ ] Clean browser (no bookmarks bar, minimal chrome)
- [ ] Dark terminal theme reads better in GIFs
- [ ] Keep it short (10-15 seconds max for GIFs)
- [ ] Show the "aha" moment - the viz updating is the money shot

### 3.3 Add .gitattributes for assets
**Priority: Low**

```
*.gif filter=lfs diff=lfs merge=lfs -text
*.png filter=lfs diff=lfs merge=lfs -text
```

Or just keep them small enough that Git LFS isn't needed.

---

## 4. Repository Hygiene

### 4.1 Clean up root directory
**Priority: High**

The root has accumulated dev artifacts. Move or delete:

| File | Action | Reason |
|------|--------|--------|
| `DESIGN.md` | Delete or move to `docs/design/` | Internal dev doc |
| `DESIGN-*.md` (4 files) | Delete or move to `docs/design/` | Internal dev docs |
| `ANALYSIS_TOOLS_USAGE.md` | Delete | Superseded by README |
| `IMPLEMENTATION_SUMMARY.md` | Delete | Internal dev doc |
| `PODCAST_OVERVIEW.md` | Delete | Not relevant to users |
| `demo_analysis_tools.py` | Move to `examples/` | Demo code |
| `demo_formats.py` | Move to `examples/` | Demo code |
| `test_server.py` | Move to `tests/` or delete | Test file in wrong place |
| `run-claude.sh` | Delete | Local dev script |
| `Dockerfile` | Keep if useful, document it | Needs review |
| `To` | Delete | Empty junk file |
| `replay-guides/` | Delete | Internal dev artifacts |
| `docs/*.md` (progress files) | Delete | Internal session state |

**After cleanup, root should contain:**
```
.
├── .github/
├── docs/
│   └── assets/
├── examples/
├── src/
├── tests/
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
└── README.md
```

### 4.2 Update .gitignore
**Priority: Medium**

Add standard Python ignores:

```gitignore
# Byte-compiled
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
venv/
.venv/
ENV/

# Distribution
dist/
build/
*.egg-info/

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project specific
.mcp.json
uv.lock
```

---

## 5. Community Files

### 5.1 CONTRIBUTING.md
**Priority: High**

Create `CONTRIBUTING.md`:

```markdown
# Contributing to MCP Graph Engine

Cheers for considering a contribution. Here's how to get involved.

## Development Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv venv && source venv/bin/activate`
3. Install in dev mode: `pip install -e ".[dev]"`
4. Run tests: `pytest`

## Making Changes

1. Fork the repo
2. Create a branch: `git checkout -b my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Submit a PR

## Code Style

- Keep it simple. Don't over-engineer.
- Add tests for new functionality.
- Update the README if you're adding user-facing features.

## Reporting Issues

Open an issue on GitHub. Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Python version and OS

## Pull Requests

- Keep PRs focused. One feature or fix per PR.
- Write a clear description of what changed and why.
- Make sure tests pass.

## Questions?

Open an issue or start a discussion on GitHub.
```

### 5.2 SECURITY.md
**Priority: Medium**

Create `SECURITY.md`:

```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

1. **Do not** open a public issue
2. Email: [your-security-email@example.com]
3. Include: description, steps to reproduce, potential impact

I'll acknowledge receipt within 48 hours and provide a timeline for a fix.

## Security Considerations

This tool runs locally and does not:
- Persist data to disk (memory-only by default)
- Make outbound network connections (except for embedding model download on first run)
- Require authentication

The visualisation server binds to `localhost` by default. If you change `VIS_HOST` to `0.0.0.0`, the visualisation will be accessible on your network.
```

### 5.3 CODE_OF_CONDUCT.md
**Priority: Low**

Use the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) standard. Keep it brief.

---

## 6. CI/CD

### 6.1 GitHub Actions workflow
**Priority: High**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest -v

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install ruff
        run: pip install ruff

      - name: Run linter
        run: ruff check src/
```

### 6.2 GitHub issue templates
**Priority: Medium**

Create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug report
about: Something's broken
title: ''
labels: bug
assignees: ''
---

**What happened?**
A clear description of the bug.

**What did you expect?**
What should have happened instead.

**Steps to reproduce**
1.
2.
3.

**Environment**
- OS:
- Python version:
- mcp-graph-engine version:

**Additional context**
Any other relevant info.
```

Create `.github/ISSUE_TEMPLATE/feature_request.md`:

```markdown
---
name: Feature request
about: Suggest an idea
title: ''
labels: enhancement
assignees: ''
---

**What problem does this solve?**
Describe the use case.

**Proposed solution**
How you think it could work.

**Alternatives considered**
Other approaches you've thought about.
```

### 6.3 PR template
**Priority: Low**

Create `.github/pull_request_template.md`:

```markdown
## What does this PR do?

Brief description.

## How to test

Steps to verify the change works.

## Checklist

- [ ] Tests pass (`pytest`)
- [ ] Docs updated (if user-facing change)
- [ ] No breaking changes (or documented in description)
```

---

## 7. Release Preparation

### 7.1 CHANGELOG.md
**Priority: High**

Create `CHANGELOG.md`:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-XX-XX

### Added
- Initial release
- Core graph operations: add_facts, add_knowledge, forget, forget_relationship
- Query tools: ask_graph, cypher_query, dump_context
- Analysis algorithms: shortest_path, all_paths, pagerank, find_cycles, connected_components, degree_centrality, transitive_reduction, subgraph
- Import/export: DOT, CSV, GraphML, JSON, Mermaid formats
- Real-time D3 visualisation with WebSocket updates
- Fuzzy node matching (exact, normalised, embedding-based)
- Multi-graph session support

[Unreleased]: https://github.com/utilitydelta/mcp-graph-engine/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/utilitydelta/mcp-graph-engine/releases/tag/v0.1.0
```

### 7.2 Version tag
**Priority: BLOCKER (at release time)**

```bash
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
```

### 7.3 PyPI publishing
**Priority: High**

1. Create account on [PyPI](https://pypi.org/) and [Test PyPI](https://test.pypi.org/)
2. Generate API tokens
3. Test publish to Test PyPI first:
   ```bash
   pip install build twine
   python -m build
   twine upload --repository testpypi dist/*
   ```
4. Verify install works: `pip install --index-url https://test.pypi.org/simple/ mcp-graph-engine`
5. Publish to real PyPI: `twine upload dist/*`

Optional: Add GitHub Action for automated releases (`.github/workflows/publish.yml`).

---

## 8. Code Quality

### 8.1 Add linting config
**Priority: Medium**

Add to `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.format]
quote-style = "double"
```

### 8.2 Run linter and fix issues
**Priority: Medium**

```bash
pip install ruff
ruff check src/ --fix
ruff format src/
```

### 8.3 Type hints audit
**Priority: Low**

The code has type hints in places. Do a pass to ensure public APIs are typed.
Not critical for v0.1.0 but nice to have.

---

## 9. Testing

### 9.1 Verify test coverage
**Priority: High**

```bash
pip install pytest-cov
pytest --cov=mcp_graph_engine --cov-report=html
open htmlcov/index.html
```

Target: >80% coverage on core modules (`graph_engine.py`, `server.py`).

### 9.2 Test on clean install
**Priority: BLOCKER**

Before release, test the full install flow:

```bash
# Fresh venv
python -m venv /tmp/test-install
source /tmp/test-install/bin/activate

# Install from source
pip install /path/to/mcp-graph-engine

# Verify it works
mcp-graph-engine --help  # or just ensure it starts
python -c "from mcp_graph_engine import server; print('OK')"
```

---

## 10. Pre-release Checklist

Final checks before pushing the button:

- [ ] LICENSE file exists
- [ ] README has no broken links
- [ ] README placeholder images replaced with real assets
- [ ] pyproject.toml has all required metadata
- [ ] CHANGELOG.md documents v0.1.0
- [ ] All tests pass on Python 3.10, 3.11, 3.12
- [ ] `pip install -e .` works on a fresh venv
- [ ] No secrets or personal paths in committed files
- [ ] .gitignore covers all dev artifacts
- [ ] GitHub repo settings:
  - [ ] Description set
  - [ ] Topics/tags added (mcp, graph, llm, etc.)
  - [ ] License detected correctly
  - [ ] Issues enabled
  - [ ] Discussions enabled (optional)
- [ ] Branch protection on `main` (optional but recommended)

---

## Priority Summary

| Priority | Items |
|----------|-------|
| **BLOCKER** | LICENSE, pyproject.toml metadata, clean install test, version tag |
| **High** | Documentation assets, repo cleanup, CONTRIBUTING.md, CHANGELOG.md, CI workflow, PyPI publishing |
| **Medium** | SECURITY.md, issue templates, linting config, .gitignore updates |
| **Low** | CODE_OF_CONDUCT.md, PR template, type hints, Git LFS |

---

## Commands Quick Reference

```bash
# Cleanup
rm -f To
rm -rf replay-guides/
rm -f run-claude.sh
rm -f DESIGN*.md ANALYSIS_TOOLS_USAGE.md IMPLEMENTATION_SUMMARY.md PODCAST_OVERVIEW.md
rm -f docs/*.md  # progress files
mv demo_*.py examples/
mv test_server.py tests/

# Setup
mkdir -p .github/workflows .github/ISSUE_TEMPLATE docs/assets

# Verify
pytest -v
ruff check src/
pip install -e . && mcp-graph-engine

# Release
python -m build
twine upload --repository testpypi dist/*
git tag -a v0.1.0 -m "Initial release"
git push origin v0.1.0
twine upload dist/*
```
