from __future__ import annotations

project = 'Wenmode'
author = 'Hsiaoming Yang'
copyright = '2026, Hsiaoming Yang'

extensions = ['myst_parser', 'sphinx_design']
myst_enable_extensions = ['colon_fence']

root_doc = 'index'
source_suffix = {
    '.md': 'markdown',
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
}

html_context = {
    'source_type': 'github',
    'source_user': 'lepture',
    'source_repo': 'wenmode',
}
