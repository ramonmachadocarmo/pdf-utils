# PDF Utils

[![GitHub stars](https://img.shields.io/github/stars/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/network/members)
[![GitHub issues](https://img.shields.io/github/issues/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/issues)
[![Last commit](https://img.shields.io/github/last-commit/ramonmachadocarmo/pdf-utils?style=flat&logo=github)](https://github.com/ramonmachadocarmo/pdf-utils/commits/main)
[![Python](https://img.shields.io/badge/python-3.13-blue?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Sponsor](https://img.shields.io/static/v1?label=Sponsor&message=%E2%9D%A4&logo=GitHub&color=%23fe8e86)](https://github.com/sponsors/ramonmachadocarmo)

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

## Support

<iframe src="https://github.com/sponsors/ramonmachadocarmo/button" title="Sponsor ramonmachadocarmo" height="32" width="114" style="border: 0; border-radius: 6px;"></iframe>

<iframe src="https://github.com/sponsors/ramonmachadocarmo/card" title="Sponsor ramonmachadocarmo" height="225" width="600" style="border: 0;"></iframe>
