from __future__ import annotations

from wenmode_myst import markdown_to_rst, target

from wenmode import RSTRenderer, Wenmode


def test_wenmode_myst_bridge_renders_sphinx_rst() -> None:
    rst = markdown_to_rst(
        """---
layout: landing
description: Example page.
---

(example)=
# Example

```{rst-class} lead
Lead with {doc}`Usage <usage>`.
```

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} Card
:link: usage
:link-type: doc

Body.
:::
::::
"""
    )

    assert rst.startswith(':layout: landing\n:description: Example page.\n')
    assert '.. _example:\n\n' in rst
    assert '.. rst-class:: lead\n\n   Lead with :doc:`Usage <usage>`.' in rst
    assert '.. grid:: 1 1 2 2\n   :gutter: 2' in rst
    assert '.. grid-item-card:: Card\n      :link: usage\n      :link-type: doc' in rst


def test_target_support_is_installable_as_plugin() -> None:
    app = Wenmode([], renderer=RSTRenderer(), plugins=[target])

    assert app.render('(example)=\n') == '.. _example:\n'


def test_wenmode_myst_bridge_keeps_code_block_body_literal() -> None:
    rst = markdown_to_rst(
        """```{code-block} python
value = node.value[start:end]
children = parser.parse_inlines(text[value_start:value_end], state)
```
"""
    )

    assert 'value = node.value[start:end]' in rst
    assert 'text[value_start:value_end]' in rst
    assert ':``' not in rst


def test_wenmode_myst_bridge_keeps_colon_fence_code_body_literal() -> None:
    rst = markdown_to_rst(
        """:::{sourcecode} python
value = node.value[start:end]
:::
"""
    )

    assert rst == '.. sourcecode:: python\n\n   value = node.value[start:end]\n'


def test_wenmode_myst_bridge_reuses_fenced_directive_for_parsed_body() -> None:
    rst = markdown_to_rst(
        """```{note} Important
Body with {doc}`Usage <usage>`.
```
"""
    )

    assert rst == '.. note:: Important\n\n   Body with :doc:`Usage <usage>`.\n'


def test_wenmode_myst_bridge_keeps_role_content_literal() -> None:
    rst = markdown_to_rst(
        """:::{tab-item} {iconify}`devicon:pypi` pip
:::
"""
    )

    assert rst == '.. tab-item:: :iconify:`devicon:pypi` pip\n'


def test_wenmode_myst_bridge_handles_inline_code_in_rst() -> None:
    rst = markdown_to_rst(
        'A [`mdast-util-directive`](https://example.com).\n\nUse `` ```{name}`` or `` {name}`content` ``.\n'
    )

    assert '`mdast-util-directive <https://example.com>`__' in rst
    assert ':literal:`\\ \\`\\`\\`{name}`' in rst
    assert ':literal:`{name}\\`content\\``' in rst
