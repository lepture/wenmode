# Renderer Fixtures

Each renderer example is a `##` heading followed by an 8-backtick `fixture`
fence. Sections are introduced by marker lines such as `.input`, `.html`,
`.markdown`, and `.rst`.

Section content keeps its text literally, except that one structural trailing
newline before the next marker is consumed. Leave a blank line before the next
marker when the value itself must end with a newline. Prefix literal section
marker lines with a backslash, such as `\.html`, to keep them as content.

## inline nodes

````````fixture
.input
## Title

Hello *em* **strong** `code` $x + y$ [link](/url "T") ![alt](/img.png)

.html
<h2>Title</h2>
<p>Hello <em>em</em> <strong>strong</strong> <code>code</code> <span class="math math-inline">x + y</span> <a href="/url" title="T">link</a> <img src="/img.png" alt="alt" /></p>

.markdown
## Title

Hello *em* **strong** `code` $x + y$ [link](/url "T") ![alt](/img.png)

.rst
Title
-----

Hello *em* **strong** ``code`` :math:`x + y` `link </url>`__ |image-1|

.. |image-1| image:: /img.png
   :alt: alt

````````

## heading ids from inline content

````````fixture
.rules
[
  "atx_heading_id",
  "image",
  "link",
  "footnote"
]
.input
# ![Alt Text](/img.png)

# ![Alt Text](/other.png)

# [^note]

[^note]: body

.html
<h1 id="alt-text"><img src="/img.png" alt="Alt Text" /></h1>
<h1 id="alt-text-1"><img src="/other.png" alt="Alt Text" /></h1>
<h1 id="note"><sup><a href="#user-content-fn-note" id="user-content-fnref-note" data-footnote-ref aria-describedby="footnote-label">1</a></sup></h1>
<section data-footnotes class="footnotes">
<h2 class="sr-only" id="footnote-label">Footnotes</h2>
<ol>
<li id="user-content-fn-note">
<p>body <a href="#user-content-fnref-note" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
</ol>
</section>

.markdown
# ![Alt Text](/img.png)

# ![Alt Text](/other.png)

# [^note]

[^note]: body

.rst
|image-1|
=========

|image-2|
=========

[#note]_
========

.. [#note] body

.. |image-1| image:: /img.png
   :alt: Alt Text

.. |image-2| image:: /other.png
   :alt: Alt Text

````````

## block nodes

````````fixture
.input
> quote

- one
- two

3. three
4. four

- loose
  
  item

- next

```py
print(1)
```

---

a  
b

.html
<blockquote>
<p>quote</p>
</blockquote>
<ul>
<li>
<p>one</p>
</li>
<li>
<p>two</p>
</li>
</ul>
<ol start="3">
<li>
<p>three</p>
</li>
<li>
<p>four</p>
</li>
</ol>
<ul>
<li>
<p>loose</p>
<p>item</p>
</li>
<li>
<p>next</p>
</li>
</ul>
<pre><code class="language-py">print(1)
</code></pre>
<hr />
<p>a<br />
b</p>

.markdown
> quote

- one

- two

3. three

4. four

- loose

  item

- next

```py
print(1)
```

---

a  
b

.rst
   quote

- one

- two

3. three

4. four

- loose

  item

- next

.. code-block:: py

   print(1)

----

a
b

.asciidoc
____
quote
____

* one

* two

. three

. four

* loose
+
item

* next

[source,py]
----
print(1)
----

'''

a +
b

````````

## commonmark roundtrip

````````fixture
.rules
[
  "thematic_break",
  "fenced_code",
  "indented_code",
  "html_block",
  "list",
  "atx_heading",
  "setext_heading",
  "blockquote",
  "hard_break",
  "autolink",
  "raw_html",
  "backslash_escape",
  "character_reference",
  "image",
  "link",
  "inline_code",
  "emphasis"
]
.roundtrip_html
true
.input
# A

> hi *there*

- one
- two

```py
print(1)
```

[link](/url "t") and ![alt](/img.png)

.html
<h1>A</h1>
<blockquote>
<p>hi <em>there</em></p>
</blockquote>
<ul>
<li>one</li>
<li>two</li>
</ul>
<pre><code class="language-py">print(1)
</code></pre>
<p><a href="/url" title="t">link</a> and <img src="/img.png" alt="alt" /></p>

.markdown
# A

> hi *there*

- one
- two

```py
print(1)
```

[link](/url "t") and ![alt](/img.png)

.rst
A
=

   hi *there*

- one
- two

.. code-block:: py

   print(1)

`link </url>`__ and |image-1|

.. |image-1| image:: /img.png
   :alt: alt

.asciidoc
= A

____
hi _there_
____

* one
* two

[source,py]
----
print(1)
----

link:/url[link] and image:/img.png[alt]

````````

## soft line break

````````fixture
.rules
[
  "hard_break"
]
.input
a
b

.html
<p>a
b</p>

.markdown
a
b

.rst
a
b

.asciidoc
a
b

````````

## footnotes

````````fixture
.rules
[
  "footnote"
]
.roundtrip_html
true
.input
a[^one]

[^one]: note

[^two]: first
  
  second

.html
<p>a<sup><a href="#user-content-fn-one" id="user-content-fnref-one" data-footnote-ref aria-describedby="footnote-label">1</a></sup></p>
<section data-footnotes class="footnotes">
<h2 class="sr-only" id="footnote-label">Footnotes</h2>
<ol>
<li id="user-content-fn-one">
<p>note <a href="#user-content-fnref-one" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
</ol>
</section>

.markdown
a[^one]

[^one]: note

[^two]: first
  
  second

.rst
a[#one]_

.. [#one] note

.. [#two] first

   second

.asciidoc
afootnote:one[note]

````````

## footnote reference order

````````fixture
.rules
[
  "footnote"
]
.input
[^one]: one

[^two]: two

[^two] [^one]

.html
<p><sup><a href="#user-content-fn-two" id="user-content-fnref-two" data-footnote-ref aria-describedby="footnote-label">1</a></sup> <sup><a href="#user-content-fn-one" id="user-content-fnref-one" data-footnote-ref aria-describedby="footnote-label">2</a></sup></p>
<section data-footnotes class="footnotes">
<h2 class="sr-only" id="footnote-label">Footnotes</h2>
<ol>
<li id="user-content-fn-two">
<p>two <a href="#user-content-fnref-two" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
<li id="user-content-fn-one">
<p>one <a href="#user-content-fnref-one" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
</ol>
</section>

.markdown
[^one]: one

[^two]: two

[^two] [^one]

.rst
.. [#one] one

.. [#two] two

[#two]_ [#one]_

````````

## repeated footnote references

````````fixture
.rules
[
  "footnote"
]
.input
[^one] [^one]

[^one]: note

.html
<p><sup><a href="#user-content-fn-one" id="user-content-fnref-one" data-footnote-ref aria-describedby="footnote-label">1</a></sup> <sup><a href="#user-content-fn-one" id="user-content-fnref-one-2" data-footnote-ref aria-describedby="footnote-label">1</a></sup></p>
<section data-footnotes class="footnotes">
<h2 class="sr-only" id="footnote-label">Footnotes</h2>
<ol>
<li id="user-content-fn-one">
<p>note <a href="#user-content-fnref-one" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a> <a href="#user-content-fnref-one-2" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
</ol>
</section>

.markdown
[^one] [^one]

[^one]: note

.rst
[#one]_ [#one]_

.. [#one] note

````````

## escaped footnote labels

````````fixture
.rules
[
  "footnote"
]
.input
[^a<b]: <note>

[^a<b]

.html
<p><sup><a href="#user-content-fn-a%3Cb" id="user-content-fnref-a%3Cb" data-footnote-ref aria-describedby="footnote-label">1</a></sup></p>
<section data-footnotes class="footnotes">
<h2 class="sr-only" id="footnote-label">Footnotes</h2>
<ol>
<li id="user-content-fn-a%3Cb">
<p>&lt;note&gt; <a href="#user-content-fnref-a%3Cb" data-footnote-backref class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>
</li>
</ol>
</section>

.markdown
[^a\<b]: \<note\>

[^a\<b]

.rst
.. [#a-b] <note>

[#a-b]_

````````

## math

````````fixture
.rules
[
  "math_block",
  "inline_math"
]
.roundtrip_html
true
.input
a $x + y$

$$
z = 1
$$

.html
<p>a <span class="math math-inline">x + y</span></p>
<div class="math math-display">z = 1
</div>

.markdown
a $x + y$

$$
z = 1
$$

.rst
a :math:`x + y`

.. math::

   z = 1

.asciidoc
a stem:[x + y]

[stem]
++++
z = 1
++++

````````

## tables and definitions

````````fixture
.input
Apple
: Fruit

| Name | Value |
| --- | --- |
| A | 1 |

.html
<dl>
<dt>Apple</dt>
<dd>Fruit</dd>
</dl>
<table>
<thead>
<tr>
<th>Name</th>
<th>Value</th>
</tr>
</thead>
<tbody>
<tr>
<td>A</td>
<td>1</td>
</tr>
</tbody>
</table>

.markdown
Apple
: Fruit

| Name | Value |
| --- | --- |
| A | 1 |

.rst
Apple
  Fruit

====  =====
Name  Value
====  =====
A     1
====  =====

.asciidoc
Apple:: Fruit

[options="header"]
|===
| Name | Value
| A | 1
|===

````````

## empty definition description

````````fixture
.input
Term
: 

.html
<dl>
<dt>Term</dt>
<dd>
</dd>
</dl>

.markdown
Term
:

.rst
Term

.asciidoc
Term::

````````

## directives

````````fixture
.input
:::note[Important]{.warning}
Body.
:::

.html
<aside class="warning admonition admonition-note">
<p class="admonition-title">Important</p>
<p>Body.</p>
</aside>

.markdown
:::note[Important]{.warning}
Body\.
:::

.rst
.. note:: Important
   :class: warning

   Body.

````````

## literal directive renderers

````````fixture
.rules
[
  "fenced_directive",
  "emphasis"
]
.input
```{code-block} python
:caption: example.py

print("*not emphasis*")
```

.html
<pre><code class="language-python">print(&quot;*not emphasis*&quot;)
</code></pre>

.markdown
```{code-block} python
:caption: example.py

print("*not emphasis*")
```

.rst
.. code-block:: python
   :caption: example.py

   print("*not emphasis*")

.asciidoc
[source,python]
----
print("*not emphasis*")
----

````````

## directive renderers without labels

````````fixture
.rules
[
  "container_directive",
  "leaf_directive"
]
.html_directives
[
  "admonition",
  "figure",
  "toc"
]
.input
:::note
body
:::

:::figure
image
:::

::toc[Contents]{min=bad}

.html
<aside class="admonition admonition-note">
<p>body</p>
</aside>
<figure>
<p>image</p>
</figure>

.markdown
:::note
body
:::

:::figure
image
:::

::toc[Contents]{min=bad}

.rst
.. note::

   body

.. figure::

   image

.. toc:: Contents
   :min: bad

````````

## block spoiler

````````fixture
.input
>! hidden *thing*
>!
>! second paragraph

.html
<div class="spoiler">
<p>hidden <em>thing</em></p>
<p>second paragraph</p>
</div>

.markdown
>! hidden *thing*
>!
>! second paragraph

.rst
.. admonition:: Spoiler

   hidden *thing*

   second paragraph

.asciidoc
[.spoiler]
--
hidden _thing_

second paragraph
--

````````

## extended inline nodes

````````fixture
.input
*[HTML]: HyperText

HTML ~~gone~~ ==mark== ^^insert^^ ^2^ ~n~ [漢(kan)] >! secret !< :kbd[Ctrl+C]

.html
<p><abbr title="HyperText">HTML</abbr> <del>gone</del> <mark>mark</mark> <ins>insert</ins> <sup>2</sup> <sub>n</sub> <ruby>漢<rt>kan</rt></ruby> <span class="spoiler">secret</span> Ctrl+C</p>

.markdown
HTML ~~gone~~ ==mark== ^^insert^^ ^2^ ~n~ [漢(kan)] >! secret !< :kbd[Ctrl\+C]

.rst
:abbr:`HTML (HyperText)` gone mark insert :sup:`2` :sub:`n` 漢 (kan) secret :kbd:`Ctrl+C`

.asciidoc
HTML [.line-through]#gone# #mark# [.underline]#insert# ^2^ ~n~ 漢 (kan) [.spoiler]#secret# Ctrl+C

````````

## raw html and unsafe urls

````````fixture
.input
# h1

<div>div</div>

a <span>b</span>

[bad](javascript:alert(1)) ![bad image](javascript:alert(1)) [safe](/safe?x=1&y=2) [mail](mailto:me@example.com)

.html
<h1>h1</h1>
&lt;div&gt;div&lt;/div&gt;
<p>a &lt;span&gt;b&lt;/span&gt;</p>
<p><a>bad</a> <img alt="bad image" /> <a href="/safe?x=1&amp;y=2">safe</a> <a href="mailto:me@example.com">mail</a></p>

.markdown
# h1

<div>div</div>

a <span>b</span>

[bad](<javascript:alert(1)>) ![bad image](<javascript:alert(1)>) [safe](/safe?x=1&y=2) [mail](mailto:me@example.com)

.rst
h1
==

.. raw:: html

   <div>div</div>

a <span>b</span>

`bad <javascript:alert(1)>`__ |image-1| `safe </safe?x=1&y=2>`__ `mail <mailto:me@example.com>`__

.. |image-1| image:: javascript:alert(1)
   :alt: bad image

````````

## raw html and unsafe urls passthrough

````````fixture
.rules
[
  "html_block",
  "raw_html",
  "link"
]
.html_options
{
  "escape": false,
  "sanitize_urls": false
}
.input
<div>div</div>

[bad](javascript:alert(1))

.html
<div>div</div>
<p><a href="javascript:alert(1)">bad</a></p>

.markdown
<div>div</div>

[bad](<javascript:alert(1)>)

.rst
.. raw:: html

   <div>div</div>

`bad <javascript:alert(1)>`__

````````

## empty containers and directive options

````````fixture
.input
>!

:::note{#intro empty}
:::

::note[Title]{#leaf empty}

:::details
Hidden
:::

.html
<div class="spoiler">
</div>
<aside id="intro" empty="" class="admonition admonition-note">
</aside>
Title<details>
<p>Hidden</p>
</details>

.markdown
>!

:::note{#intro empty}
:::

::note[Title]{#leaf empty}

:::details
Hidden
:::

.rst
.. admonition:: Spoiler

.. note::
   :name: intro
   :empty:

.. note:: Title
   :name: leaf
   :empty:

.. details::

   Hidden

````````

## bare directive renderers

````````fixture
.rules
[
  "leaf_directive",
  "container_directive"
]
.html_directives
[]
.input
::note

:::note
:::

.html

.markdown
::note

:::note
:::

.rst
.. note::

.. note::

````````

## aligned table

````````fixture
.input
| Left | Center | Right |
| :--- | :---: | ---: |
| a<br>b | c | d |

.html
<table>
<thead>
<tr>
<th align="left">Left</th>
<th align="center">Center</th>
<th align="right">Right</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left">a&lt;br&gt;b</td>
<td align="center">c</td>
<td align="right">d</td>
</tr>
</tbody>
</table>

.markdown
| Left | Center | Right |
| :--- | :---: | ---: |
| a<br>b | c | d |

.rst
======  ======  =====
Left    Center  Right
======  ======  =====
a<br>b  c       d
======  ======  =====

.asciidoc
[cols="<,^,>",options="header"]
|===
| Left | Center | Right
| apass:[<br>]b | c | d
|===

````````

## empty footnote definition output

````````fixture
.rules
[
  "footnote"
]
.input
[^empty]:

.html

.markdown
[^empty]:

.rst
.. [#empty]

````````

## empty list item

````````fixture
.input
-
- two

.html
<ul>
<li></li>
<li>two</li>
</ul>

.markdown
-
- two

.rst
-
- two

````````

## reference labels from inline content

````````fixture
.input
[![alt](/img.png)][image-ref]

[a  
b][break-ref]

[image-ref]: /image-link
[break-ref]: /break-link

.html
<p><a href="/image-link"><img src="/img.png" alt="alt" /></a></p>
<p><a href="/break-link">a<br />
b</a></p>

.markdown
[![alt](/img.png)](/image-link)

[a  
b](/break-link)

.rst
`alt </image-link>`__

`ab </break-link>`__

````````

## task list

````````fixture
.input
- [x] done
- [ ] todo

.html
<ul>
<li><input checked="" disabled="" type="checkbox"> done</li>
<li><input disabled="" type="checkbox"> todo</li>
</ul>

.markdown
- [x] done
- [ ] todo

.rst
- [x] done
- [ ] todo

````````

## loose task list

````````fixture
.input
- [x] done

  more

.html
<ul>
<li>
<p><input checked="" disabled="" type="checkbox"> done</p>
<p>more</p>
</li>
</ul>

.markdown
- [x] done

  more

.rst
- [x] done

      more

````````

## nested list block children

````````fixture
.rules
[
  "list",
  "blockquote",
  "fenced_code"
]
.input
- parent
  - child

- quote
  > nested quote

- code
  ```py
  print(1)
  ```

.html
<ul>
<li>
<p>parent</p>
<ul>
<li>child</li>
</ul>
</li>
<li>
<p>quote</p>
<blockquote>
<p>nested quote</p>
</blockquote>
</li>
<li>
<p>code</p>
<pre><code class="language-py">print(1)
</code></pre>
</li>
</ul>

.markdown
- parent

  - child

- quote

  > nested quote

- code
  ```py
  print(1)
  ```

.rst
- parent

  - child

- quote

     nested quote

- code

  .. code-block:: py

     print(1)

.asciidoc
* parent
** child

* quote
+
____
nested quote
____

* code
+
[source,py]
----
print(1)
----

````````

## short table body row

````````fixture
.input
a | b | c
| --- | --- | --- |
| 1 | 2 |

.html
<table>
<thead>
<tr>
<th>a</th>
<th>b</th>
<th>c</th>
</tr>
</thead>
<tbody>
<tr>
<td>1</td>
<td>2</td>
<td></td>
</tr>
</tbody>
</table>

.markdown
| a | b | c |
| --- | --- | --- |
| 1 | 2 |  |

.rst
===  ===  ===
a    b    c
===  ===  ===
1    2
===  ===  ===

.asciidoc
[options="header"]
|===
| a | b | c
| 1 | 2 | 
|===

````````

## loose definition list

````````fixture
.input
Term
: one

    two

.html
<dl>
<dt>Term</dt>
<dd>
<p>one</p>
<p>two</p>
</dd>
</dl>

.markdown
Term
: one
    
    two

.rst
Term
  one

  two

.asciidoc
Term::
+
one

two

````````

## definition list without trailing newline

````````fixture
.rules
[
  "definition_list"
]
.input
Term
: desc
.html
<dl>
<dt>Term</dt>
<dd>desc</dd>
</dl>

.markdown
Term
: desc

.rst
Term
  desc

.asciidoc
Term:: desc

````````

## abbreviation without title

````````fixture
.input
*[HTML]:

HTML

.html
<p><abbr>HTML</abbr></p>

.markdown
HTML

.rst
HTML

.asciidoc
HTML

````````

## code fence grows past contained fence

````````fixture
.input
````meta
contains ``` fence
````

.html
<pre><code class="language-meta">contains ``` fence
</code></pre>

.markdown
````meta
contains ``` fence
````

.rst
.. code-block:: meta

   contains ``` fence

````````

## tab indented code

````````fixture
.input
	print(1)
	  indented

.html
<pre><code>print(1)
  indented
</code></pre>

.markdown
```
print(1)
  indented
```

.rst
::

   print(1)
     indented

````````

## partially tab indented code

````````fixture
.rules
[
  "indented_code"
]
.input
 	code

.html
<pre><code>code
</code></pre>

.markdown
```
code
```

.rst
::

   code

````````

## inline code with backticks

````````fixture
.input
`` `x` ``

.html
<p><code>`x`</code></p>

.markdown
`` `x` ``

.rst
:literal:`\`x\``

````````

## link and image escaping

````````fixture
.input
[link](</a b(1)> "a \"quote\"") ![a*b](</a)b> "title")

.html
<p><a href="/a%20b(1)" title="a &quot;quote&quot;">link</a> <img src="/a)b" alt="a*b" title="title" /></p>

.markdown
[link](</a%20b(1)> "a \"quote\"") ![a\*b](</a)b> "title")

.rst
`link </a%20b(1)>`__ |image-1|

.. |image-1| image:: /a)b
   :alt: a*b
   :title: title

.asciidoc
link:/a%20b(1)[link] image:/a)b[a*b,title="title"]

````````

## inline escaping edges

````````fixture
.rules
[
  "backslash_escape",
  "inline_code",
  "link",
  "image"
]
.input
Escaped: \` \* \_ \{ \} \[ \] \< \> \( \) \# \+ \- \. \! \|.

Code: ``  padded  `` and `` `tick` ``.

Link: [a <b>](</a b(1)> "a \"quote\"") ![x*y](</img path(1).png> "img \"t\"")

.html
<p>Escaped: ` * _ { } [ ] &lt; &gt; ( ) # + - . ! |.</p>
<p>Code: <code> padded </code> and <code>`tick`</code>.</p>
<p>Link: <a href="/a%20b(1)" title="a &quot;quote&quot;">a &lt;b&gt;</a> <img src="/img%20path(1).png" alt="x*y" title="img &quot;t&quot;" /></p>

.markdown
Escaped: \` \* \_ \{ \} \[ \] \< \> \( \) \# \+ \- \. \! \|\.

Code: `  padded  ` and `` `tick` ``\.

Link: [a \<b\>](</a%20b(1)> "a \"quote\"") ![x\*y](</img%20path(1).png> "img \"t\"")

.rst
Escaped: \` \* _ { } [ ] < > ( ) # + - . ! \|.

Code: `` padded `` and :literal:`\`tick\``.

Link: `a \<b\> </a%20b(1)>`__ |image-1|

.. |image-1| image:: /img%20path(1).png
   :alt: x*y
   :title: img "t"

.asciidoc
Escaped: \` \* \_ { } \[ \] < > ( ) \# + - . ! \|.

Code: + padded + and +`tick`+.

Link: link:/a%20b(1)[a <b>] image:/img%20path(1).png[x*y,title="img \"t\""]

````````

## empty document

````````fixture
.input

.html

.markdown

.rst

.asciidoc

````````

## empty blockquote

````````fixture
.rules
[
  "blockquote"
]
.input
>

.html
<blockquote>
</blockquote>

.markdown
>

.rst

.asciidoc
____
____

````````

## ordered list default start

````````fixture
.rules
[
  "list"
]
.input
1. one
2. two

.html
<ol>
<li>one</li>
<li>two</li>
</ol>

.markdown
1. one
2. two

.rst
#. one
#. two

.asciidoc
. one
. two

````````

## unclosed fenced code with meta

````````fixture
.rules
[
  "fenced_code"
]
.input
```py meta
print(1)
.html
<pre><code class="language-py">print(1)</code></pre>

.markdown
```py meta
print(1)
```

.rst
.. code-block:: py

   print(1)

````````

## bare leaf directive quoted attributes

````````fixture
.rules
[
  "leaf_directive"
]
.html_directives
[]
.input
::note[Title]{title="a b" empty}

.html
Title
.markdown
::note[Title]{title="a b" empty}

.rst
.. note:: Title
   :title: a b
   :empty:

````````

## leaf directive empty id attribute

````````fixture
.rules
[
  "leaf_directive"
]
.html_directives
[]
.input
::note{id=}

.html

.markdown
::note

.rst
.. note::
   :name:

````````

## unclosed math block without trailing newline

````````fixture
.rules
[
  "math_block"
]
.input
$$
x
.html
<div class="math math-display">x</div>

.markdown
$$
x
$$

.rst
.. math::

   x

````````

## multiline raw html rst block

````````fixture
.rules
[
  "html_block"
]
.input
<div>one

two</div>

.html
&lt;div&gt;one
<p>two&lt;/div&gt;</p>

.markdown
<div>one

two\</div\>

.rst
.. raw:: html

   <div>one

two</div>

````````

## html container renderers

````````fixture
.rules
[
  "html_container",
  "atx_heading"
]
.html_options
{
  "escape": false
}
.input
<section class="hero" hidden>
# Title
</section>

.html
<section class="hero" hidden>
<h1>Title</h1>
</section>

.markdown
<section class="hero" hidden>
# Title
</section>

.rst
.. raw:: html

   <section class="hero" hidden>

Title
=====

.. raw:: html

   </section>

.asciidoc
++++
<section class="hero" hidden>
++++

= Title

++++
</section>
++++

````````
