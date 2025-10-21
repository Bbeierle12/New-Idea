VENV?=.venv

ifeq ($(OS),Windows_NT)
PYTHON?=$(VENV)/Scripts/python.exe
else
PYTHON?=$(VENV)/bin/python
endif

.PHONY: venv
venv:
	python -m venv $(VENV)

.PHONY: install
install: venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

.PHONY: lint
lint:
	$(PYTHON) -m black glyphx
	$(PYTHON) -m isort glyphx
	$(PYTHON) -m ruff check glyphx
	$(PYTHON) -m mypy glyphx

.PHONY: test
test:
	$(PYTHON) -m pytest

.PHONY: format
format:
	$(PYTHON) -m black glyphx
	$(PYTHON) -m isort glyphx

.PHONY: bundle-win
bundle-win:
	$(PYTHON) -m PyInstaller --noconfirm --clean --name glyphx --windowed --onefile glyphx/app/__main__.py

.PHONY: bundle-mac
bundle-mac:
	$(PYTHON) -m PyInstaller --noconfirm --clean --name glyphx --windowed --onefile glyphx/app/__main__.py

.PHONY: bundle-linux
bundle-linux:
	$(PYTHON) -m PyInstaller --noconfirm --clean --name glyphx --onefile glyphx/app/__main__.py

.PHONY: clean-bundles
clean-bundles:
	$(PYTHON) - <<'PY'
import pathlib
import shutil

for name in ["build", "dist", "glyphx.spec"]:
    path = pathlib.Path(name)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()
PY
