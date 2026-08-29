\
# Changelog

All notable changes to this project will be documented in this file.
The format is (read: strives to be) based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

----

## [0.1.11] - 08-29-2026
### Changed:
- Regain python 3.9.support by adding typer dep range
- Remove maxson-build-utils as a dep.

### Added:
- resources.py, to carry and deliver logos and gui theme files.
- standard group empty placeholder.

----

## [0.1.10] - 08-28-2026
### Fixed:
- SVG asset reference URL

----

## [0.1.9] - 08-28-2026
### Changed:
- Add back the config_mngr.set() usage in launch_configured_website()
- Improve stderr messaging in case of config.set() with key mutation.
- Provide CLI guidance for adding a website.
- Separate out url as stdout.
- Blindwindow protected and warning provided if TKinter is not available.

----

## [0.1.8] - 08-28-2026
### Fixed:
- Replace '‑' (U+2011) with common hyphen, '-', in ./docs/Spot*.md

----

## [0.1.7] - 08-28-2026
### Added:
- shiv runner, build-pyz.yml, based on `uv run mbu build shiv`.

----

## [0.1.6] - 08-28-2026
### Added:
- Blindwindow lives, `mgui blindwindow`
- Why: Route console stderr and stdout to blindwindow, to either duplicate or display what is otherwise hidden. Namely for MSIX deployed CLI's.
- Render console stderr and stdout to a TKinter based REPL widget masquerading as a log pange.
- Use Case: When calling a CLI packaged inside of a MSIX that has been delivered via the Microsoft Store. This use case typically does not allow prints. Example: pdflinkcheck.exe serve --help

----

## [0.1.5] - 08-27-2026
### Added:
- Allow config path to be injected into launch configured website, in args and in CLI.

---

## [0.1.4] - 08-27-2026
### Added:
- external_web_launch.launch_configured_website()
- Launch target dir.

---

## [0.1.3] - 08-27-2026
### Added:
- splash.py and tk_utils.py copied from pdflinkcheck

---

## [0.1.2] - 08-27-2026
### Fixed:
- In publish.yml, improve CLI help test by adding "uv run"

---

## [0.1.1] - 08-27-2026
### Added:
- Ensure that TCL files are carried, with MANIFEST.in file.

---

## [0.1.0] - 08-27-2026
### Added:
- Scaffolded with maxson-build-utils
- Ensure that GUI launches from CLI
- Include tkinter forest theme

---
