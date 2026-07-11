from __future__ import annotations

from collections.abc import Iterator
from typing import BinaryIO

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from wenmode import Wenmode
from wenmode.presets import streaming

preview = Wenmode(streaming)

app = FastAPI(title='Wenmode FastAPI streaming example')


def iter_upload_lines(file: BinaryIO, encoding: str = 'utf-8') -> Iterator[str]:
    for line in file:
        yield line.decode(encoding)


def stream_uploaded_markdown(upload: UploadFile) -> Iterator[str]:
    try:
        upload.file.seek(0)
        yield '<article class="markdown-preview">\n'
        yield from preview.stream(iter_upload_lines(upload.file))
        yield '</article>\n'
    finally:
        upload.file.close()


@app.get('/', response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Wenmode FastAPI streaming example</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      margin: 2rem;
    }
    main {
      display: grid;
      gap: 1rem;
      max-width: 56rem;
    }
    #preview {
      border-top: 1px solid #ddd;
      padding-top: 1rem;
    }
  </style>
</head>
<body>
  <main>
    <h1>Wenmode FastAPI streaming example</h1>
    <form id="streaming-form" action="/streaming" method="post" enctype="multipart/form-data">
      <p>
        <input name="file" type="file" accept=".md,.markdown,text/markdown" required>
      </p>
      <p><button type="submit">Stream file</button></p>
    </form>
    <section id="preview"></section>
  </main>
  <script>
    const form = document.getElementById('streaming-form')
    const preview = document.getElementById('preview')

    form.addEventListener('submit', async (event) => {
      event.preventDefault()
      preview.innerHTML = ''
      const response = await fetch('/streaming', {
        method: 'POST',
        body: new FormData(form)
      })
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
      while (true) {
        const {value, done} = await reader.read()
        if (done) break
        preview.insertAdjacentHTML('beforeend', value)
      }
    })
  </script>
</body>
</html>
"""


@app.post('/streaming')
def render_streaming(file: UploadFile = File(...)) -> StreamingResponse:
    return StreamingResponse(stream_uploaded_markdown(file), media_type='text/html; charset=utf-8')
