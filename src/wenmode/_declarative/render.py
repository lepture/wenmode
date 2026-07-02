from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Literal, TypeAlias, cast

from wenmode.nodes import Node
from wenmode.renderers import BaseRenderer, RenderContext, RenderHandler

from .spec import RenderTemplate

RendererHandlers: TypeAlias = Mapping[str, Mapping[str, RenderHandler]]
TemplatePart: TypeAlias = Literal['children', 'value'] | str


def renderer_handlers_from_templates(renderers: Mapping[str, Mapping[str, RenderTemplate]]) -> RendererHandlers:
    return {
        renderer_name: {
            node_type: render_template(template)
            for node_type, template in templates.items()
        }
        for renderer_name, templates in renderers.items()
    }


def render_template(template: RenderTemplate) -> RenderHandler:
    parts = compile_template(template.template)
    needs_children = 'children' in parts
    needs_value = 'value' in parts

    if len(parts) == 3 and parts[1] == 'children' and isinstance(parts[0], str) and isinstance(parts[2], str):
        prefix, _, suffix = parts

        def render_children_template(renderer: BaseRenderer, node: Node, context: RenderContext) -> str:
            children = ''
            node_children = getattr(node, 'children', None)
            if isinstance(node_children, list):
                children = renderer.render_children(cast(list[Node], node_children), context)
            return prefix + children + suffix

        return render_children_template

    if len(parts) == 3 and parts[1] == 'value' and isinstance(parts[0], str) and isinstance(parts[2], str):
        prefix, _, suffix = parts

        def render_value_template(renderer: BaseRenderer, node: Node, context: RenderContext) -> str:
            value = getattr(node, 'value', '')
            if not isinstance(value, str):
                value = ''
            return prefix + value + suffix

        return render_value_template

    def handler(renderer: BaseRenderer, node: Node, context: RenderContext) -> str:
        children = ''
        if needs_children:
            node_children = getattr(node, 'children', None)
            if isinstance(node_children, list):
                children = renderer.render_children(cast(list[Node], node_children), context)

        value = getattr(node, 'value', '')
        if needs_value and not isinstance(value, str):
            value = ''

        rendered = []
        for part in parts:
            if part == 'children':
                rendered.append(children)
            elif part == 'value':
                rendered.append(value)
            else:
                rendered.append(part)
        return ''.join(rendered)

    return handler


def compile_template(template: str) -> tuple[TemplatePart, ...]:
    parts: list[TemplatePart] = []
    start = 0
    for match in re.finditer(r'\{(?:children|value)\}', template):
        if match.start() > start:
            parts.append(template[start : match.start()])
        name = match.group(0)[1:-1]
        parts.append(cast(Literal['children', 'value'], name))
        start = match.end()
    if start < len(template):
        parts.append(template[start:])
    return tuple(parts)
