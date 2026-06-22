# wenmode-fastapi

This is a local FastAPI example that streams Markdown preview HTML through
Wenmode. It is intended as a small integration package in this repository and is
not published to PyPI.

Run the app from the repository root:

```bash
uv run --directory examples/wenmode-fastapi --locked uvicorn wenmode_fastapi:app --reload
```

Post a Markdown file to render your own preview:

```bash
curl -N \
  -F 'file=@README.md;type=text/markdown' \
  http://127.0.0.1:8000/streaming
```

The example uses Wenmode's `streaming` preset and FastAPI's
`StreamingResponse`. The `/streaming` endpoint accepts a multipart Markdown file
upload and passes a decoded line iterator to Wenmode, so rendered HTML chunks are
sent as Wenmode parses top-level blocks. This keeps response delivery
incremental while preserving Wenmode's default safe HTML rendering policy.
