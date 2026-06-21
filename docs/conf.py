from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'examples' / 'wenmode-myst' / 'src'))

project = 'Wenmode'
author = 'Hsiaoming Yang'
copyright = '2026, Hsiaoming Yang'

extensions = [
    'wenmode_myst',
    'sphinx.ext.autodoc',
    'sphinx_design',
    'sphinx_iconify',
    'shibuya.sponsors',
]
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'
iconify_script_url = ''
sponsors_json_url = 'https://cdn.jsdelivr.net/gh/lepture/lepture/sponsors.json'

root_doc = 'index'
source_suffix = {
    '.md': 'markdown',
    '.rst': 'restructuredtext',
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

html_theme = 'shibuya'
html_title = 'Wenmode'
html_baseurl = 'https://wenmode.lepture.com/'
html_static_path = ['_static']
html_logo = '_static/light-logo.svg'
html_favicon = '_static/wenmode-mark.svg'
html_css_files = [
    'custom.css',
]

html_theme_options = {
    'accent_color': 'red',
    'light_logo': '_static/light-logo.svg',
    'dark_logo': '_static/dark-logo.svg',
    'discussion_url': 'https://github.com/lepture/wenmode/discussions',
    'github_url': 'https://github.com/lepture/wenmode',
    'twitter_url': 'https://twitter.com/lepture',
    'twitter_creator': 'lepture',
    'twitter_site': 'lepture',
    'nav_links': [
        {
            'title': 'Docs',
            'url': 'usage',
        },
        {
            'title': 'Support me',
            'url': 'sponsors',
        },
    ],
}

html_context = {
    'source_type': 'github',
    'source_user': 'lepture',
    'source_repo': 'wenmode',
}
