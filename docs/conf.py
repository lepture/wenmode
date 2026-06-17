from __future__ import annotations

project = 'Wenmode'
author = 'Hsiaoming Yang'
copyright = '2026, Hsiaoming Yang'

extensions = ['myst_parser']

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
    'discussion_url': 'https://github.com/lepture/wenmode/discussions',
    'accent_color': 'red',
    'light_logo': '_static/light-logo.svg',
    'dark_logo': '_static/dark-logo.svg',
}
