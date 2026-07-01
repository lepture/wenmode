Wenmode
=======

|Build Status| |PyPI version| |Code Coverage| |Maintainability Rating| |Security Rating|

.. |Build Status| image:: https://img.shields.io/github/actions/workflow/status/lepture/wenmode/test.yml?logo=github&label=test
   :target: https://github.com/lepture/wenmode/actions
   :alt: Build Status

.. |PyPI version| image:: https://img.shields.io/pypi/v/wenmode?logo=python&logoColor=fff&labelColor=3776ab
   :target: https://pypi.org/project/wenmode
   :alt: PyPI version

.. |Code Coverage| image:: https://img.shields.io/codecov/c/github/lepture/wenmode
   :target: https://codecov.io/gh/lepture/wenmode
   :alt: Code Coverage

.. |Maintainability Rating| image:: https://sonarcloud.io/api/project_badges/measure?project=lepture_wenmode&metric=sqale_rating
   :target: https://sonarcloud.io/summary/new_code?id=lepture_wenmode
   :alt: Maintainability Rating

.. |Security Rating| image:: https://sonarcloud.io/api/project_badges/measure?project=lepture_wenmode&metric=security_rating
   :target: https://sonarcloud.io/summary/new_code?id=lepture_wenmode
   :alt: Security Rating

Wenmode is a composable Markdown toolkit for Python by the same author as
`Mistune <https://mistune.lepture.com/>`__. It is a rewrite informed by Mistune's
design, with a stronger focus on explicit rule composition, mdast-compatible AST
output, extension state, and pluggable rendering.

The top-level ``Wenmode`` class combines a parser and a renderer. By default it
parses CommonMark-style Markdown and renders HTML.

Documentation: `https://wenmode.lepture.com <https://wenmode.lepture.com>`__

Use Wenmode when you need one or more of these behaviors:

- render Markdown to HTML with safe defaults for user-authored content,
- choose the exact Markdown rules your application accepts,
- inspect or store an mdast-compatible AST,
- build a custom Markdown dialect with parser rules and renderer handlers,
- stream HTML output from Markdown input.

Installation
------------

.. code-block:: bash

   pip install wenmode

Run the CLI without installing it permanently:

.. code-block:: bash

   uvx wenmode render --preset=github README.md
   uvx wenmode ast --preset=github README.md

After installation, use either the console script or Python module entry point:

.. code-block:: bash

   wenmode render README.md --preset=github
   python -m wenmode ast README.md --positions

Quick start
-----------

.. code-block:: python

   from wenmode import Wenmode

   wen = Wenmode()

   text = '''
   # Hello

   This is **wenmode**.
   '''
   expected = '''
   <h1>Hello</h1>
   <p>This is <strong>wenmode</strong>.</p>
   '''

   html = wen.render(text)
   assert html == expected.lstrip()

Use ``parse()`` when you need the mdast-compatible syntax tree:

.. code-block:: python

   from wenmode import Wenmode

   wen = Wenmode()
   text = 'A [link](https://example.com).'

   tree = wen.parse(text)
   ast = tree.to_ast()

   assert ast == {
       'type': 'root',
       'children': [
           {
               'type': 'paragraph',
               'children': [
                   {'type': 'text', 'value': 'A '},
                   {
                       'type': 'link',
                       'children': [{'type': 'text', 'value': 'link'}],
                       'url': 'https://example.com',
                   },
                   {'type': 'text', 'value': '.'},
               ],
           }
       ],
   }

Enable source positions when you need editor ranges, diagnostics, or AST-based
tooling:

.. code-block:: python

   from wenmode import Wenmode

   wen = Wenmode(positions=True)
   ast = wen.parse('A **bold**.\n').to_ast()

   assert ast['children'][0] == {
       'type': 'paragraph',
       'position': {
           'start': {'line': 1, 'column': 1, 'offset': 0},
           'end': {'line': 2, 'column': 1, 'offset': 12}
       },
       'children': [
           {
               'type': 'text',
               'position': {
                   'start': {'line': 1, 'column': 1, 'offset': 0},
                   'end': {'line': 1, 'column': 3, 'offset': 2}
               },
               'value': 'A '
           },
           {
               'type': 'strong',
               'position': {
                   'start': {'line': 1, 'column': 3, 'offset': 2},
                   'end': {'line': 1, 'column': 11, 'offset': 10}
               },
               'children': [
                   {
                       'type': 'text',
                       'position': {
                           'start': {'line': 1, 'column': 5, 'offset': 4},
                           'end': {'line': 1, 'column': 9, 'offset': 8}
                       },
                       'value': 'bold'
                   }
               ]
           },
           {
               'type': 'text',
               'position': {
                   'start': {'line': 1, 'column': 11, 'offset': 10},
                   'end': {'line': 1, 'column': 12, 'offset': 11}
               },
               'value': '.'
           }
       ]
   }

Pass a different renderer when you want another output format, such as
reStructuredText or AsciiDoc:

.. code-block:: python

   from wenmode import AsciiDocRenderer, Wenmode

   wen = Wenmode(renderer=AsciiDocRenderer())

   text = '# Hello'
   expected = '''
   = Hello
   '''

   asciidoc = wen.render(text)
   assert asciidoc == expected.lstrip()

Rules, presets, and plugins
---------------------------

Most applications start with a preset:

- ``commonmark``, the default CommonMark-style rule set,
- ``github``, for GitHub-flavored Markdown features such as tables and task
  lists,
- ``streaming``, for incremental HTML output.

Rules are opt-in and composable. ``Wenmode()`` uses the ``commonmark`` preset by
default; pass an explicit rule list when you want a custom Markdown dialect.

.. code-block:: python

   from wenmode import Wenmode
   from wenmode.rules import AtxHeading, FencedCode, Image, InlineCode, Link

   wen = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])
   text = '''
   # h1

   hi `code` **strong**
   '''
   expected = '''
   <h1>h1</h1>
   <p>hi <code>code</code> **strong**</p>
   '''

   assert wen.render(text) == expected.lstrip()

Because ``Emphasis`` is not enabled above, ``**strong**`` stays as text.

Use ``Parser`` directly when you only need an AST and want to choose rendering
separately:

.. code-block:: python

   from wenmode import HTMLRenderer, Parser
   from wenmode.presets import commonmark

   parser = Parser(commonmark)
   text = '# Hello'

   tree = parser.parse(text)

   html = HTMLRenderer().render(tree)

Use the ``github`` preset for GitHub-flavored Markdown features such as tables,
task lists, strikethrough, extended autolinks, and footnotes:

.. code-block:: python

   from wenmode import Wenmode
   from wenmode.presets import github

   wen = Wenmode(github)

Use built-in plugins for non-standard syntax, document metadata, and rendering
behavior such as front matter, math, definition lists, abbreviations, spoilers,
ruby text, HTML smart punctuation, and extra inline formatting:

.. code-block:: python

   from wenmode import Wenmode
   from wenmode.plugins import math

   wen = Wenmode(plugins=[math])

   assert wen.render('Inline $x + y$.\n') == (
       '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
   )

Benchmark
---------

Wenmode is designed so enabling more rules adds limited dispatch overhead. The
benchmark script compares Markdown-to-HTML throughput across Wenmode and the
libraries covered by the migration guides:

.. code-block:: bash

   uv run --locked --group benchmark python scripts/benchmark.py --case all

``wenmode-core`` uses CommonMark-style rules plus pipe tables, with raw HTML
passthrough and URL sanitization disabled for parity with the other HTML
renderers. Mistune, Python-Markdown, markdown-it-py, and markdown2 enable table
support; Marko uses its broader GFM helper; ``commonmark.py`` is included as a
CommonMark-only baseline because it has no pipe table support.

``wenmode-all`` uses the ``github`` preset plus Wenmode's built-in plugins,
including front matter, math, definition lists, abbreviations, spoilers, ruby
text, and additional inline formatting. These extra rules are mostly unused by the
benchmark corpora, so this target measures dispatch overhead rather than a
syntax-equivalent comparison.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown resets the same reusable
``Markdown`` instance before each conversion.

Versions used in these snapshots:

===============  =======
Library          Version
===============  =======
wenmode          0.8.0
mistune          3.3.2
python-markdown  3.10.2
markdown-it-py   4.2.0
markdown2        2.5.5
marko            2.2.3
commonmark.py    0.9.2
===============  =======

Mean time from one local Python 3.12.9 ``--case all`` run:

=========  =========  ===============  ========  =====  =======
Case       Bytes      Library          Mean      MB/s   vs core
=========  =========  ===============  ========  =====  =======
docs       116,875    wenmode-core     16.56ms   7.54   1.00x
docs       116,875    wenmode-all      18.33ms   6.64   0.90x
docs       116,875    mistune          22.28ms   5.67   0.74x
docs       116,875    python-markdown  69.72ms   1.69   0.24x
docs       116,875    markdown-it-py   34.57ms   3.51   0.48x
docs       116,875    markdown2        129.98ms  0.91   0.13x
docs       116,875    marko            119.55ms  1.01   0.14x
docs       116,875    commonmark.py    83.65ms   1.47   0.20x
rust-book  1,225,464  wenmode-core     163.27ms  7.66   1.00x
rust-book  1,225,464  wenmode-all      197.30ms  7.01   0.83x
rust-book  1,225,464  mistune          246.29ms  5.54   0.66x
rust-book  1,225,464  python-markdown  662.25ms  1.93   0.25x
rust-book  1,225,464  markdown-it-py   358.07ms  3.53   0.46x
rust-book  1,225,464  markdown2        4.296s    0.30   0.04x
rust-book  1,225,464  marko            1.175s    1.07   0.14x
rust-book  1,225,464  commonmark.py    10.026s   0.13   0.02x
progit     502,090    wenmode-core     31.54ms   18.04  1.00x
progit     502,090    wenmode-all      35.96ms   15.51  0.88x
progit     502,090    mistune          42.83ms   11.77  0.74x
progit     502,090    python-markdown  149.84ms  3.49   0.21x
progit     502,090    markdown-it-py   77.83ms   7.28   0.41x
progit     502,090    markdown2        1.483s    0.35   0.02x
progit     502,090    marko            356.82ms  1.45   0.09x
progit     502,090    commonmark.py    346.01ms  1.48   0.09x
=========  =========  ===============  ========  =====  =======

In this run, ``wenmode-all`` remains faster than the other parsers even after
loading many extra rules that the benchmark inputs mostly do not use.

Benchmark numbers depend on hardware, Python version, corpus, and parser
configuration. See the full methodology in the
`Benchmarks <https://wenmode.lepture.com/benchmarks/>`__ documentation.

Streaming
---------

Use the ``streaming`` preset when you want to render HTML chunks without waiting
for the entire document to be parsed and rendered:

.. code-block:: python

   from wenmode import Wenmode
   from wenmode.presets import streaming

   wen = Wenmode(streaming)

   text = '''
   # Hello

   A [link](/url).
   '''

   for chunk in wen.stream(text):
       send(chunk)

The returned iterator can be passed to streaming responses in frameworks such
as Django, Flask, and FastAPI. The ``streaming`` preset keeps tables,
strikethrough, direct links, and direct images enabled, while reference-style
links, footnotes, and other deferred document-wide transforms stay out of the
streaming path.

Learn more
----------

- `Usage <https://wenmode.lepture.com/usage/>`__ for the main APIs.
- `Presets <https://wenmode.lepture.com/presets/>`__ for choosing a rule set.
- `Security <https://wenmode.lepture.com/security/>`__ for raw HTML and URL
  handling.
- `Plugins <https://wenmode.lepture.com/plugins/>`__ for built-in extensions.
- `Migration guides <https://wenmode.lepture.com/migration/>`__ for moving from
  other Python Markdown parsers.
