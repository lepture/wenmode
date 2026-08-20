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

The top-level ``Wenmode`` class combines a parser and a renderer. By default,
``Wenmode`` parses CommonMark-style Markdown and renders HTML.

Documentation: `https://wenmode.lepture.com <https://wenmode.lepture.com>`__

Use Wenmode to:

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

Set ``positions=True`` to include source ranges for editor integration,
diagnostics, or AST-based tooling:

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

Pass a renderer when you need reStructuredText or AsciiDoc output:

.. code-block:: python

   from wenmode import AsciiDocRenderer, Wenmode

   wen = Wenmode(renderer=AsciiDocRenderer())

   text = '# Hello'
   expected = '= Hello\n'

   asciidoc = wen.render(text)
   assert asciidoc == expected

Rules, presets, and plugins
---------------------------

Most applications start with a preset:

- ``commonmark``, the default CommonMark-style rule set,
- ``github``, for GitHub-flavored Markdown features such as tables and task
  lists,
- ``streaming``, for incremental HTML output.

Rules are opt-in and composable. ``Wenmode()`` uses the ``commonmark`` preset by
default. Pass an explicit rule list to define a custom Markdown dialect.

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
   from wenmode.plugins import inline_math

   wen = Wenmode(plugins=[inline_math])

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

``wenmode-core`` uses CommonMark-style rules plus pipe tables. It disables raw HTML
passthrough and URL sanitization to match the other HTML renderers. Mistune,
Python-Markdown, markdown-it-py, and markdown2 enable table support. Marko uses
its broader GFM helper. ``commonmark.py`` is a CommonMark-only baseline because it
does not support pipe tables.

``wenmode-all`` uses the ``github`` preset plus Wenmode's built-in plugins,
including front matter, math, definition lists, abbreviations, spoilers, ruby
text, heading IDs, GitHub alerts, and additional inline formatting. The benchmark
corpora use few of these extra rules. This target measures rule dispatch
overhead, not equivalent syntax coverage.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown resets the same reusable
``Markdown`` instance before each conversion.

Versions used in these snapshots:

===============  =======
Library          Version
===============  =======
wenmode          0.14.0
mistune          3.3.4
mistletoe        1.6.0
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
docs       138,514    wenmode-core     21.05ms   6.91   1.00x
docs       138,514    wenmode-all      24.74ms   5.81   0.85x
docs       138,514    mistune          25.26ms   5.54   0.83x
docs       138,514    mistletoe        53.46ms   2.60   0.39x
docs       138,514    python-markdown  78.48ms   1.84   0.27x
docs       138,514    markdown-it-py   42.04ms   3.44   0.50x
docs       138,514    markdown2        181.37ms  0.78   0.12x
docs       138,514    marko            173.29ms  0.87   0.12x
docs       138,514    commonmark.py    115.60ms  1.39   0.18x
rust-book  1,226,057  wenmode-core     168.42ms  7.54   1.00x
rust-book  1,226,057  wenmode-all      187.55ms  6.72   0.90x
rust-book  1,226,057  mistune          224.58ms  5.60   0.75x
rust-book  1,226,057  mistletoe        468.09ms  2.63   0.36x
rust-book  1,226,057  python-markdown  588.85ms  2.10   0.29x
rust-book  1,226,057  markdown-it-py   337.24ms  3.71   0.50x
rust-book  1,226,057  markdown2        4.117s    0.30   0.04x
rust-book  1,226,057  marko            1.092s    1.12   0.15x
rust-book  1,226,057  commonmark.py    9.831s    0.13   0.02x
progit     502,090    wenmode-core     29.05ms   17.30  1.00x
progit     502,090    wenmode-all      38.04ms   14.70  0.76x
progit     502,090    mistune          46.85ms   11.87  0.62x
progit     502,090    mistletoe        147.81ms  3.53   0.20x
progit     502,090    python-markdown  139.58ms  3.73   0.21x
progit     502,090    markdown-it-py   74.58ms   7.73   0.39x
progit     502,090    markdown2        1.452s    0.35   0.02x
progit     502,090    marko            331.42ms  1.54   0.09x
progit     502,090    commonmark.py    338.07ms  1.61   0.09x
=========  =========  ===============  ========  =====  =======

In this run, ``wenmode-all`` remains faster than the other parsers even after
loading many extra rules that the benchmark inputs mostly do not use.

Benchmark numbers depend on hardware, Python version, corpus, and parser
configuration. See the full methodology in the
`Benchmarks <https://wenmode.lepture.com/benchmarks/>`__ documentation.

Streaming
---------

Use the ``streaming`` preset to render HTML chunks before the complete document is
parsed and rendered:

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

Pass the returned iterator to a streaming response in Django, Flask, FastAPI,
or another framework. The ``streaming`` preset keeps tables, strikethrough, direct
links, and direct images enabled. It excludes reference-style links, footnotes,
and other deferred document-wide transforms.

Learn more
----------

- `Usage <https://wenmode.lepture.com/usage/>`__ for the main APIs.
- `Presets <https://wenmode.lepture.com/presets/>`__ for choosing a rule set.
- `Security <https://wenmode.lepture.com/security/>`__ for raw HTML and URL
  handling.
- `Plugins <https://wenmode.lepture.com/plugins/>`__ for built-in extensions.
- `Migration guides <https://wenmode.lepture.com/migration/>`__ for moving from
  other Python Markdown parsers.
