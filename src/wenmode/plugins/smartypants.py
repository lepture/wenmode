from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from wenmode.nodes import Text
from wenmode.renderers import RenderContext
from wenmode.renderers.html import SOFT_BREAK_SPACE_RE, HTMLRenderContext, HTMLRenderer

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class SmartypantsState:
    """Mutable typography state carried by one render context."""

    previous: str | None = None
    double_open: bool = True
    single_open: bool = True


def setup(
    wenmode: Wenmode,
    quotes: bool = True,
    dashes: bool = True,
    ellipses: bool = True,
    **options: Any,
) -> None:
    """Install smart punctuation rendering for plain text nodes."""

    def render_text_node(
        renderer: HTMLRenderer,
        node: Text,
        context: HTMLRenderContext,
    ) -> str:
        value = SOFT_BREAK_SPACE_RE.sub('', node.value)
        text = smarten(value, state_for(context), quotes=quotes, dashes=dashes, ellipses=ellipses)
        return renderer.escape_html(text)

    wenmode.register_renderer_handlers(
        {
            'html': {
                Text.type: render_text_node,
            }
        }
    )


def state_for(context: RenderContext) -> SmartypantsState:
    state = getattr(context, '_smartypants_state', None)
    if isinstance(state, SmartypantsState):
        return state
    state = SmartypantsState()
    setattr(cast(Any, context), '_smartypants_state', state)
    return state


def smarten(
    value: str,
    state: SmartypantsState | None = None,
    *,
    quotes: bool = True,
    dashes: bool = True,
    ellipses: bool = True,
) -> str:
    """Return ``value`` with common ASCII punctuation converted to Unicode."""
    if state is None:
        state = SmartypantsState()

    parts: list[str] = []
    index = 0
    while index < len(value):
        if ellipses and value.startswith('...', index):
            parts.append('…')
            state.previous = '…'
            index += 3
            continue

        if dashes and value.startswith('---', index):
            parts.append('—')
            state.previous = '—'
            index += 3
            continue

        if dashes and value.startswith('--', index):
            parts.append('–')
            state.previous = '–'
            index += 2
            continue

        char = value[index]
        if quotes and char == '"':
            char = smart_double_quote(state, next_char(value, index))
        elif quotes and char == "'":
            char = smart_single_quote(state, next_char(value, index))

        parts.append(char)
        state.previous = char
        index += 1

    return ''.join(parts)


def smart_double_quote(state: SmartypantsState, next_: str | None) -> str:
    if state.double_open:
        if is_opening_context(state.previous) or not is_closing_context(next_):
            state.double_open = False
            return '“'
        return '”'

    state.double_open = True
    return '”'


def smart_single_quote(state: SmartypantsState, next_: str | None) -> str:
    previous = state.previous
    if previous is not None and next_ is not None and previous.isalnum() and next_.isalnum():
        return '’'
    if next_ is not None and next_.isdigit() and is_opening_context(previous):
        return '’'
    if previous is not None and previous.isalnum() and state.single_open:
        return '’'

    if state.single_open:
        if is_opening_context(previous) or not is_closing_context(next_):
            state.single_open = False
            return '‘'
        return '’'

    state.single_open = True
    return '’'


def next_char(value: str, index: int) -> str | None:
    next_index = index + 1
    if next_index >= len(value):
        return None
    return value[next_index]


def is_opening_context(char: str | None) -> bool:
    return char is None or char.isspace() or char in '([{/\\<'


def is_closing_context(char: str | None) -> bool:
    return char is None or char.isspace() or char in '.,;:!?)]}%'
