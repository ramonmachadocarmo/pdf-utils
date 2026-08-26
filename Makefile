.PHONY: help setup install run dev desktop build-windows installer test clean

PYTHON_VERSION := 3.13.11
POETRY := pyenv exec poetry

SHELL := cmd.exe
.SHELLFLAGS := /c

.DEFAULT_GOAL := help

help: ## List available commands
	@powershell -NoProfile -Command "Get-Content Makefile | ForEach-Object { if ($$_ -match '^([a-zA-Z0-9_-]+):.*?##\s*(.*)$$') { '{0,-12} {1}' -f $$matches[1], $$matches[2] } }"

setup: ## Install Python via pyenv and Poetry on that Python
	pyenv install -s $(PYTHON_VERSION)
	pyenv local $(PYTHON_VERSION)
	pyenv exec python -m pip install --upgrade pip poetry
	pyenv rehash
	$(POETRY) config virtualenvs.in-project true --local

install: ## Create project .venv and install dependencies
	$(POETRY) config virtualenvs.in-project true --local
	powershell -NoProfile -Command "if (-not (Test-Path '.venv\Scripts\python.exe')) { pyenv exec python -m venv .venv }; pyenv exec poetry env use (Resolve-Path '.venv\Scripts\python.exe')"
	$(POETRY) install

run: ## Start server at http://127.0.0.1:8000
	$(POETRY) run uvicorn app.main:app --host 127.0.0.1 --port 8000

dev: ## Start with hot reload
	$(POETRY) run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

desktop: ## Run as a native desktop window
	$(POETRY) run python -m app.desktop

build-windows: ## Build a standalone Windows .exe (dist/PDF Utils.exe)
	$(POETRY) run pyinstaller --noconfirm pdf-utils.spec

installer: build-windows ## Build a Windows installer (installer_output/PDF-Utils-Setup.exe). Needs Inno Setup.
	powershell -NoProfile -Command "$$candidates = @((Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source, \"$$env:LOCALAPPDATA\Programs\InnoSetup6\ISCC.exe\", 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe', 'C:\Program Files\Inno Setup 6\ISCC.exe'); $$iscc = $$candidates | Where-Object { $$_ -and (Test-Path $$_) } | Select-Object -First 1; if (-not $$iscc) { Write-Error 'Inno Setup (ISCC.exe) not found. Install it from https://jrsoftware.org/isinfo.php'; exit 1 }; & $$iscc installer.iss"

test: ## Run unit tests with coverage gate
	$(POETRY) run pytest -q

clean: ## Remove .venv, caches, and storage
	-$(POETRY) env remove --all
	-powershell -NoProfile -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .venv, .pytest_cache, build, dist; if (Test-Path storage) { Get-ChildItem storage -Exclude .gitkeep | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue }; Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force"
