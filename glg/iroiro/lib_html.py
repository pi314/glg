from html.parser import HTMLParser

from .internal_utils import exporter
export, __all__ = exporter()

from .lib_math import interval


self_closing_tags = {
        'area', 'base', 'br', 'col', 'embed', 'hr', 'img',
        'input', 'link', 'meta', 'param', 'source', 'track', 'wbr',
        }


@export
class HTML(HTMLParser):
    def __init__(self, source, keep_comments=False, keep_spaces='pre'):
        super().__init__()

        if isinstance(keep_spaces, str):
            keep_spaces = {keep_spaces}
        else:
            try:
                keep_spaces = set(keep_spaces)
            except TypeError:
                keep_spaces = bool(keep_spaces)

        self.keep_comments = keep_comments
        self.keep_spaces = keep_spaces

        self.decl = None
        self.roots = []
        self.stack = []

        if hasattr(source, 'read') and callable(source.read):
            self.feed(source.read())
        elif isinstance(source, str):
            self.feed(source)
        else:
            raise TypeError('Unrecognized source:', repr(source))

    @property
    def root(self):
        if self.roots:
            return self.roots[0]

    def __getattr__(self, name):
        for root in self.roots:
            if name == root.name:
                return root

        for root in self.roots:
            try:
                return getattr(root, name)
            except AttributeError:
                pass

        raise AttributeError(name)

    def handle_decl(self, decl):
        self.decl = decl

    def handle_comment(self, data):
        if not self.keep_comments:
            return

        elem = HTMLComment(data)

        if not self.stack:
            self.roots.append(elem)

        if self.stack:
            self.stack[-1].append(elem)

    def handle_starttag(self, tag, attrs):
        elem = HTMLElement(tag, attrs)

        if not self.stack:
            self.roots.append(elem)

        if self.stack:
            self.stack[-1].append(elem)

        if tag not in self_closing_tags:
            self.stack.append(elem)

    def handle_endtag(self, tag):
        if not self.stack:
            return

        if tag in self_closing_tags:
            return

        if self.stack[-1].name == tag:
            self.stack.pop()
            return

        for i in interval(len(self.stack) - 1, 0, close=True):
            if self.stack[i].name == tag:
                self.stack[i:] = []
                break

    def handle_data(self, data):
        keep_spaces = None
        if isinstance(self.keep_spaces, set):
            keep_spaces = self.keep_spaces & set(node.name for node in self.stack)
        else:
            keep_spaces = bool(self.keep_spaces)

        if not keep_spaces:
            data = data.strip()

        if not data:
            return

        if self.stack:
            self.stack[-1].append(data)


class HTMLComment:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return '<!--' + self.data + '-->'

    def __str__(self):
        return self.data

    def __eq__(self, other):
        return self is other or str(self) == other


class HTMLElementDataSetProxy:
    def __init__(self, elem):
        self.elem = elem

    def __getattr__(self, name):
        return self.elem.attrs.get('data-' + name)


class HTMLElement:
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = dict(attrs)
        self.childnodes = []

    def __repr__(self):
        if self.attrs:
            attr = ' ' + ' '.join([f'{attr}="{value}"'
                                   for attr, value in self.attrs.items()])
        else:
            attr = ''
        if self.name in self_closing_tags:
            return f'<{self.name}{attr}>'

        return (f'<{self.name}{attr}>' +
                ''.join(child if isinstance(child, str) else repr(child) for child in self.childnodes) +
                f'</{self.name}>')

    @property
    def tagname(self):
        return self.name

    @property
    def classlist(self):
        return self.attrs.get('class', '').split()

    @property
    def dataset(self):
        return HTMLElementDataSetProxy(self)

    @property
    def children(self):
        return [child
                for child in self.childnodes
                if not isinstance(child, str)
                ]

    @property
    def innerText(self):
        tokens = [child if isinstance(child, str) else child.innerText
                  for child in self.childnodes]

        if not tokens:
            return ''

        # Join child innerTexts with
        # - empty, if one of the connecting ends already have space
        # - space, otherwise
        ret, *tokens = tokens
        for token in tokens:
            if (not ret or ret.endswith((' ', '\n'))) or (not token or token.startswith((' ', '\n'))):
                ret += token
            else:
                ret += ' ' + token
        return ret

    def __getattr__(self, name):
        if name in self.attrs:
            return self.attrs[name]

        for child in self.children:
            if child.name == name:
                return child

        raise AttributeError(name)

    def append(self, elem):
        self.childnodes.append(elem)
