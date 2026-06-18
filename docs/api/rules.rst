.. _api-rules:

Rules
=====

.. automodule:: wenmode.rules

For a compact lookup table of preset membership, generated nodes, rule options,
and streaming compatibility, see :ref:`rule-matrix`.

Rule Base Classes
-----------------

.. autoclass:: wenmode.rules.Rule
   :members:

.. autoclass:: wenmode.rules.BlockRule
   :members:

.. autoclass:: wenmode.rules.ContinueRule
   :members:

.. autoclass:: wenmode.rules.InlineRule
   :members:

.. autoclass:: wenmode.rules.RootTransform
   :members:

Block Rules
-----------

.. autoclass:: wenmode.rules.ThematicBreak

.. autoclass:: wenmode.rules.FencedCode

.. autoclass:: wenmode.rules.IndentedCode

.. autoclass:: wenmode.rules.HtmlBlock

.. autoclass:: wenmode.rules.List

.. autoclass:: wenmode.rules.AtxHeading

.. autoclass:: wenmode.rules.SetextHeading

.. autoclass:: wenmode.rules.Blockquote

.. autoclass:: wenmode.rules.Table

.. autoclass:: wenmode.rules.FootnoteDefinition

.. autoclass:: wenmode.rules.Abbreviation

.. autoclass:: wenmode.rules.DefinitionList

.. autoclass:: wenmode.rules.MathBlock

.. autoclass:: wenmode.rules.BlockSpoiler

.. autoclass:: wenmode.rules.LeafDirective

.. autoclass:: wenmode.rules.ContainerDirective

.. autoclass:: wenmode.rules.FencedDirective

.. autoclass:: wenmode.rules.ReferenceDefinition

Inline Rules
------------

.. autoclass:: wenmode.rules.BackslashEscape

.. autoclass:: wenmode.rules.CharacterReference

.. autoclass:: wenmode.rules.HardBreak

.. autoclass:: wenmode.rules.Autolink

.. autoclass:: wenmode.rules.RawHtml

.. autoclass:: wenmode.rules.Image

.. autoclass:: wenmode.rules.Link

.. autoclass:: wenmode.rules.InlineCode

.. autoclass:: wenmode.rules.Emphasis

.. autoclass:: wenmode.rules.Strikethrough

.. autoclass:: wenmode.rules.ExtendedAutolink

.. autoclass:: wenmode.rules.Mark

.. autoclass:: wenmode.rules.Insert

.. autoclass:: wenmode.rules.Superscript

.. autoclass:: wenmode.rules.Subscript

.. autoclass:: wenmode.rules.Ruby

.. autoclass:: wenmode.rules.InlineSpoiler

.. autoclass:: wenmode.rules.InlineMath

.. autoclass:: wenmode.rules.TextDirective

.. autoclass:: wenmode.rules.Role

.. autoclass:: wenmode.rules.Footnote
