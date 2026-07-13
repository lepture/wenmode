from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from docx.document import Document as DocumentObject

from .converter import DOCXRenderer, markdown_to_docx, save_markdown_as_docx

__all__ = ['DOCXRenderer', 'main', 'markdown_to_docx', 'save_markdown_as_docx']


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Convert Markdown to DOCX with Wenmode.')
    parser.add_argument('input', type=Path, help='Markdown input file')
    parser.add_argument('output', type=Path, help='DOCX output file')
    args = parser.parse_args(argv)

    source = args.input.read_text(encoding='utf-8')
    document: DocumentObject = markdown_to_docx(source)
    title = args.input.stem.replace('-', ' ').replace('_', ' ').strip()
    if title:
        document.core_properties.title = title
    document.save(args.output)
    return 0
