# PDF Utils

[![GitHub stars](https://img.shields.io/github/stars/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/network/members)
[![GitHub issues](https://img.shields.io/github/issues/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/issues)
[![Last commit](https://img.shields.io/github/last-commit/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/commits/main)
[![Python](https://img.shields.io/badge/python-3.13-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Sponsor](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/ramonmachadocarmo)

Local PDF reader and editor: pen, text, highlight, stamp, signature, search, zoom, rotate, and convert to PNG, JPEG, WEBP, or DOCX.

Everything runs on your machine — files are not uploaded to the cloud.

UI languages: **English**, **Portuguese (BR)**, **Spanish**.

## Screenshots

![Home](docs/screenshots/home.png)

![Editor](docs/screenshots/editor.png)

![Editor with annotations](docs/screenshots/editor-annotated.png)

## Features

### Reading
- Page-by-page preview with thumbnails
- Zoom in/out and pan with the **Hand** tool
- Text search with hit navigation
- Rotate page by 90°
- **Night** mode
- **Focus view** — hides chrome for distraction-free reading

### Editing
| Tool | What it does |
|------|----------------|
| **Pen** | Freehand stroke (color and width) |
| **Highlight** | Semi-transparent rectangle |
| **Text** | Insert free text at click point |
| **Signature** | Blue stroke for signing |
| **Stamp** | `Approved`, `Paid`, or today's date |
| **Hand** | Pan the viewport |

- **Undo** removes the last edit
- **Clear** removes unsaved edits on the current page
- **Save edits** writes annotations into the working PDF
- **Download PDF** downloads the current file

### Conversion
| Format | Notes |
|--------|-------|
| PNG / JPEG / WEBP | One image per page (ZIP if multipage) |
| DOCX | Export via `pdf2docx` |

UI parameters: `format`, `dpi` (72–600), and `quality` (1–100, images).

### Internationalization
- Locale files in `app/static/i18n/` (`en`, `pt-BR`, `es`)
- Language selector in the header (persisted in `localStorage`)
- Browser language is detected on first visit
- API / backend messages are in English

## Requirements

- [pyenv](https://github.com/pyenv/pyenv) (or pyenv-win on Windows)
- Python **3.13.11** (see `.python-version`)
- [Poetry](https://python-poetry.org/) (installed by `make setup`)
- `make` on your PATH

## Setup

Poetry uses an in-project virtualenv (`.venv`).

```bash
make setup    # install Python 3.13.11 via pyenv + Poetry
make install  # create .venv and install dependencies
```

| Command | Effect |
|---------|--------|
| `make setup` | `pyenv install 3.13.11`, local Poetry, `virtualenvs.in-project` |
| `make install` | Ensure `.venv`, point Poetry at it, `poetry install` |
| `make clean` | Remove `.venv`, caches, and `storage/` files |

### Main dependencies

- **FastAPI** + **Uvicorn** — API and static UI
- **PyMuPDF** — read, preview, search, annotate, rotate
- **pdf2docx** — DOCX export
- **Pillow** — image formats

### Local storage

```text
storage/
  uploads/<job_id>/source.pdf    # original PDF
  uploads/<job_id>/working.pdf   # PDF with saved edits
  outputs/<job_id>/              # conversion results
```

Cleared by `make clean` (keeps `.gitkeep`).

## Run

```bash
make dev    # hot reload — development
make run    # server without reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Interactive API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

## Using the UI

1. **Open a PDF** — drop it on the dashed area or click to choose.
2. **Navigate** — thumbnails, arrows, or page indicators.
3. **Search** — enter a term, then **Search** / **Previous** / **Next**.
4. **Zoom** — `−` / `+`; use **Hand** to pan.
5. **Edit** — pick a tool and draw or click on the page.
6. **Stamp** — choose type (`Approved` / `Paid` / `Date`) and click.
7. **Save** — **Save edits** writes the working PDF; **Download PDF** downloads it.
8. **Convert** — pick format/DPI/quality and click **Convert**.
9. **Focus reading** — **Focus view** hides chrome; **Show UI** restores it.
10. **Language** — switch English / Portugues (BR) / Espanol in the header.

Tips:
- Edits are only written after **Save edits**.
- Switching pages keeps unsaved edits in memory per page.
- Stamp labels on the canvas follow the UI language; labels burned into the PDF use English (`APPROVED` / `PAID`).

## Tests

```bash
make test
```

Runs `poetry run pytest -q` with coverage for `app` and fails under **95%**.

## API

Base path: `/api`

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/api/upload` | Upload PDF (`multipart`, field `file`) → `{ job_id, filename, page_count, ... }` |
| `GET` | `/api/preview/{job_id}/{page}` | Page preview PNG (`?dpi=160`) |
| `GET` | `/api/search/{job_id}?q=` | Text search → normalized hits |
| `POST` | `/api/annotate/{job_id}` | Persist edits (strokes, texts, highlights, stamps) |
| `POST` | `/api/rotate/{job_id}` | Rotate page (`page_index`, `degrees`) |
| `GET` | `/api/download/{job_id}` | Download working PDF |
| `POST` | `/api/convert/{job_id}` | Convert (`format`, `dpi`, `quality`) |

Upload example:

```bash
curl -F "file=@document.pdf" http://127.0.0.1:8000/api/upload
```

Convert example:

```bash
curl -X POST "http://127.0.0.1:8000/api/convert/<job_id>" \
  -F "format=png" \
  -F "dpi=150" \
  -F "quality=90" \
  -o output.zip
```

## Project layout

```text
app/
  api/          # routes and schemas
  domain/       # domain models
  services/     # reader, editor, converter
  static/       # UI + i18n locales
  config.py     # paths (storage, static)
  main.py       # FastAPI app
docs/screenshots/
tests/
storage/        # uploads and outputs (runtime)
```

## Make commands

```text
make help      List commands
make setup     Python + Poetry
make install   Dependencies in .venv
make run       Server
make dev       Server with reload
make test      Pytest (+ coverage gate)
make clean     Clear venv/cache/storage
```

## Support

If this project helps you, consider sponsoring:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub_Sponsors-ea4aaa?style=for-the-badge&logo=github)](https://github.com/sponsors/ramonmachadocarmo)
