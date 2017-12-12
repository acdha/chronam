# encoding: utf-8
from __future__ import absolute_import, print_function

from collections import deque
from urllib2 import urlopen
import os

import re

try:
    from xml.etree import cElementTree as ElementTree
except ImportError:
    from xml.etree import ElementTree


# trash leading/trailing punctuation and apostropes
NON_LEXEMES = re.compile('''^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$|'s$''')


def ocr_extractor(ocr_file_or_url):
    """
    Extracts the text and word coordinates from an OCR XML file
    """

    page_text = {}  # Dictionary keyed by language
    word_coordinates = {}

    width = None
    height = None

    if os.path.exists(ocr_file_or_url):
        f = open(ocr_file_or_url, 'rb')
    else:
        f = urlopen(ocr_file_or_url)
    tree = ElementTree.parse(f)
    f.close()

    doc = tree.getroot()

    # Unfortunately, namespace usage is inconsistent and the usability-hostile
    # design of every XML parser means we can't ignore them:

    m = re.match(r'{(.+)}(alto)', doc.tag)
    if not m:
        raise RuntimeError('Expected ALTO XML but received %s' % doc.tag)

    xmlns, tag = m.groups()

    page = doc.find('.//{%s}Page' % xmlns)
    if page is None:
        raise RuntimeError('%s does not appear to contain a Page element')

    width = page.get('WIDTH')
    height = page.get('HEIGHT')

    line_buffer = deque()

    for text_block in page.findall('.//{%s}TextBlock' % xmlns):
        lang = text_block.get('language', 'eng')

        # We'll avoid a lookup for each line by saving a reference:
        lang_text = page_text.setdefault(lang, [])

        for line in text_block.findall('{%s}TextLine' % xmlns):
            for string in line.findall('{%s}String' % xmlns):
                content = string.get("CONTENT")
                coord = (string.get('HPOS'), string.get('VPOS'),
                         string.get('WIDTH'), string.get('HEIGHT'))

                line_buffer.append(content)

                # solr's WordDelimiterFilterFactory tokenizes based on punctuation
                # which removes it from highlighting, so it's important to remove
                # it here as well or else we'll look up words that don't match
                word = NON_LEXEMES.sub('', content)
                if word:
                    word_coordinates.setdefault(word, []).append(coord)

            lang_text.append(' '.join(line_buffer))
            line_buffer.clear()

    coords_struct = {"width": width, "height": height, "coords": word_coordinates}

    all_page_text = {lang: "\n".join(page_lines) for lang, page_lines in page_text.iteritems()}

    return all_page_text, coords_struct


if __name__ == '__main__':
    from timeit import default_timer
    import sys

    for f in sys.argv[1:]:
        start_time = default_timer()
        text, coords = ocr_extractor(f)
        elapsed_time = default_timer() - start_time
        print('Parsed %s in %0.04f seconds' % (f, elapsed_time))
