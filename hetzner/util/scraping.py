try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser


class CSRFParser(HTMLParser):
    def __init__(self, field_name):
        HTMLParser.__init__(self)
        self.field_name = field_name
        self.csrf_token = None

    def handle_starttag(self, tag, attrs):
        if tag != 'input':
            return
        attrdict = dict(attrs)
        if attrdict.get('name', '') == self.field_name:
            self.csrf_token = attrdict.get('value', None)
    handle_startendtag = handle_starttag
