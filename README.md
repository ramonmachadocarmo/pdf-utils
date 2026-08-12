# PDF Utils

Leitor/editor local de PDF com caneta livre e conversao para PNG, JPEG, WEBP ou DOCX.

## Stack

- pyenv (`3.13.11` via `.python-version`)
- Poetry (`.venv` in-project)
- FastAPI + PyMuPDF + pdf2docx

## Estrutura

```text
app/
  api/         # HTTP (routes + schemas)
  domain/      # modelos
  services/    # PDF read / edit / convert
  static/      # UI
  config.py
  main.py
```

## Setup

```bash
make setup
make install
```

## Run

```bash
make dev
```

http://127.0.0.1:8000

## API

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/api/upload` | envia PDF |
| GET | `/api/preview/{job_id}/{page}` | preview PNG |
| POST | `/api/annotate/{job_id}` | grava risco/caneta |
| GET | `/api/download/{job_id}` | baixa PDF editado |
| POST | `/api/convert/{job_id}` | converte (`format`, `dpi`, `quality`) |
