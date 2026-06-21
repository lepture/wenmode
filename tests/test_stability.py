from __future__ import annotations

from io import StringIO

import pytest

from wenmode import StreamingUnsupportedError, Wenmode
from wenmode.plugins import abbr, math, spoiler
from wenmode.presets import streaming


def test_positions_survive_plugin_root_transforms() -> None:
    app = Wenmode(positions=True).use(abbr)
    root = app.parse('*[HTML]: HyperText\n\nHTML and HTML\n')

    paragraph = root.to_ast()['children'][0]
    first, middle, second = paragraph['children']

    assert first == {
        'type': 'abbreviation',
        'position': {
            'start': {'line': 3, 'column': 1, 'offset': 20},
            'end': {'line': 3, 'column': 5, 'offset': 24},
        },
        'children': [
            {
                'type': 'text',
                'position': {
                    'start': {'line': 3, 'column': 1, 'offset': 20},
                    'end': {'line': 3, 'column': 5, 'offset': 24},
                },
                'value': 'HTML',
            }
        ],
        'title': 'HyperText',
    }
    assert middle == {
        'type': 'text',
        'position': {
            'start': {'line': 3, 'column': 5, 'offset': 24},
            'end': {'line': 3, 'column': 10, 'offset': 29},
        },
        'value': ' and ',
    }
    assert second['position'] == {
        'start': {'line': 3, 'column': 10, 'offset': 29},
        'end': {'line': 3, 'column': 14, 'offset': 33},
    }


def test_plugin_state_is_created_per_parse() -> None:
    app = Wenmode().use(abbr)

    assert app.render('*[HTML]: HyperText\n\nHTML\n') == '<p><abbr title="HyperText">HTML</abbr></p>\n'
    assert app.render('HTML\n') == '<p>HTML</p>\n'


def test_streaming_preset_supports_streaming_compatible_plugins() -> None:
    app = Wenmode(streaming).use(math).use(spoiler)
    markdown = 'A $x$ and >! hidden !<.\n\n- [x] done\n'

    assert ''.join(app.stream(markdown)) == app.render(markdown)
    assert ''.join(app.stream(StringIO(markdown))) == app.render(markdown)


def test_streaming_rejects_plugins_with_deferred_transforms() -> None:
    with pytest.raises(StreamingUnsupportedError, match='deferred inline transforms'):
        next(Wenmode(streaming).use(abbr).stream('HTML\n\n*[HTML]: HyperText\n'))


def test_streaming_positions_remain_offset_only_for_plugin_nodes() -> None:
    parser = Wenmode(streaming, positions=True).use(math).use(spoiler).parser
    markdown = 'A $x$ and >! hidden !<.\n'

    paragraph = next(parser.parse_iter(markdown)).to_ast()

    assert paragraph['position'] == {'start': {'offset': 0}, 'end': {'offset': 24}}
    assert paragraph['children'][1] == {
        'type': 'inlineMath',
        'position': {'start': {'offset': 2}, 'end': {'offset': 5}},
        'value': 'x',
    }
    assert paragraph['children'][3] == {
        'type': 'inlineSpoiler',
        'position': {'start': {'offset': 10}, 'end': {'offset': 22}},
        'children': [
            {
                'type': 'text',
                'position': {'start': {'offset': 13}, 'end': {'offset': 19}},
                'value': 'hidden',
            }
        ],
    }
