# encoding: utf-8
from __future__ import absolute_import, print_function

from collections import deque

import re
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, feature_namespaces

# trash leading/trailing punctuation and apostropes
non_lexemes = re.compile('''^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$|'s$''')


class OCRHandler(ContentHandler):

    def __init__(self):
        self._page = {}
        self._line = deque()
        self._coords = {}
        self._language = 'eng'
        self.width = None
        self.height = None

    def startElement(self, tag, attrs):
        if tag == 'String':
            content = attrs.get("CONTENT")
            coord = (attrs.get('HPOS'), attrs.get('VPOS'),
                     attrs.get('WIDTH'), attrs.get('HEIGHT'))

            self._line.append(content)

            # solr's WordDelimiterFilterFactory tokenizes based on punctuation
            # which removes it from highlighting, so it's important to remove
            # it here as well or else we'll look up words that don't match
            word = non_lexemes.sub('', content)
            if word:
                self._coords.setdefault(word, []).append(coord)
        elif tag == 'Page':
            assert self.width is None
            assert self.height is None
            self.width = attrs.get('WIDTH')
            self.height = attrs.get('HEIGHT')
        elif tag == 'TextBlock':
            self._language = attrs.get('language', 'eng')

    def endElement(self, tag):
        if tag == 'TextLine':
            l = ' '.join(self._line)

            self._line.clear()

            self._page.setdefault(self._language, []).append(l)

        if tag == 'Page':
            for l in self._page.keys():
                self._page[l] = '\n'.join(self._page[l])

    def text(self):
        return "\n".join(self._page.values())

    def lang_text(self):
        return self._page

    def coords(self):
        return {"width": self.width, "height": self.height,
                "coords": self._coords}


def ocr_extractor(ocr_file):
    """
    looks at the ocr xml file on disk, extracts the plain text and
    word coordinates from them.
    """

    handler = OCRHandler()
    parser = make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(feature_namespaces, 0)
    parser.parse(ocr_file)

    return handler.lang_text(), handler.coords()


if __name__ == '__main__':
    from timeit import default_timer
    import sys

    for f in sys.argv[1:]:
        start_time = default_timer()
        text, coords = ocr_extractor(f)
        elapsed_time = default_timer() - start_time
        print('Parsed %s in %0.04f seconds' % (f, elapsed_time))
