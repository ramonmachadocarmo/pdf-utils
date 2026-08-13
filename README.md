# PDF Utils

Leitor e editor local de PDF: caneta, texto, destaque, carimbo, assinatura, busca, zoom e conversao para PNG, JPEG, WEBP ou DOCX.

## Stack

- pyenv (`3.13.11` via `.python-version`)
- Poetry (`.venv` in-project)
- FastAPI + PyMuPDF + pdf2docx

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

## Testes

```bash
make test
```

## Uso

1. Solte um PDF na area de upload.
2. Edite com caneta, destaque, texto, assinatura ou carimbo.
3. Use busca, zoom, girar e modo noite.
4. **Salvar edicao** grava no PDF; **Baixar PDF** baixa o arquivo.
5. **Converter** exporta para imagem ou DOCX.
6. **So visualizar** esconde a interface.

## API

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/api/upload` | envia PDF |
| GET | `/api/preview/{job_id}/{page}` | preview PNG |
| GET | `/api/search/{job_id}?q=` | busca texto |
| POST | `/api/annotate/{job_id}` | grava edicoes |
| POST | `/api/rotate/{job_id}` | gira pagina |
| GET | `/api/download/{job_id}` | baixa PDF editado |
| POST | `/api/convert/{job_id}` | converte (`format`, `dpi`, `quality`) |
