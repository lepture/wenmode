from __future__ import annotations

from fastapi.testclient import TestClient
from wenmode_fastapi import app


def test_streaming_endpoint_streams_uploaded_markdown_file() -> None:
    client = TestClient(app)

    response = client.post(
        '/streaming',
        files={
            'file': (
                'posted.md',
                b'# Posted\n\nBody with **strong** text and ~~old~~ text.\n\n| A | B |\n| --- | --- |\nx | y\n',
                'text/markdown',
            )
        },
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/html')
    assert response.text.startswith('<article class="markdown-preview">')
    assert '<h1>Posted</h1>' in response.text
    assert '<p>Body with <strong>strong</strong> text and <del>old</del> text.</p>' in response.text
    assert '<table>' in response.text
    assert '<td>y</td>' in response.text
    assert response.text.endswith('</article>\n')


def test_demo_endpoint_is_not_registered() -> None:
    client = TestClient(app)

    response = client.get('/demo')

    assert response.status_code == 404
