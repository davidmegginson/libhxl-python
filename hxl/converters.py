"""Data-conversion classes

This module holds classes for converting to HXL from other formats, or
from HXL to other formats. Current, the only class is L{Tagger} (for
adding tags to non-HXL tabular data on the fly), but we will add more
converters soon, especially for formats like GeoJSON.

@author: David Megginson
@organization: UNOCHA
@license: Public Domain
@date: Started April 2015
@see: http://hxlstandard.org

"""

import hxl, re


class Tagger(hxl.io.AbstractInput):
    """Add HXL hashtags to a CSV-like input stream.

    Usage::
    
      input = open('data.csv', 'r')
      specs = [('Cluster', '#sector'), ('Organi', '#org'), ('province', '#adm1+es')]
      tagger = Tagger(input, specs)

    The tagger object acts as a L{hxl.io.AbstractInput} source, which you can
    use with the L{hxl.data} function like this::

      source = hxl.data(Tagger(input, specs)).with_rows('org=unicef').sort()

    """

    def __init__(self, input, specs=[]):
        """Construct a new Tagger object.

        The input spec is a list of tuples, where the first item is a
        substring to match (case-/space-/punctuation-insensitive), and
        the second item is the HXL tag spec to use. Example::

          [('Cluster', '#sector'), ('Organi', '#org'), ('province', '#adm1+es')]

        @param input: an input stream of some kind.
        @param specs: the input specs, as described above (default: [])
        """
        self.specs = [(hxl.common.normalise_string(spec[0]), spec[1]) for spec in specs]
        self.input = iter(input)
        self._cache = []
        self._found_tags = False

    def __next__(self):
        """Return the next line of input (including the new tags)."""
        if not self._found_tags:
            # Search the first 25 rows for a match.
            if self._add_tags():
                self._found_tags = True
            else:
                # if no match, through an exception
                raise hxl.common.HXLException("Tagging failed")
        if len(self._cache) > 0:
            # read from the cache, first
            return self._cache.pop(0)
        else:
            return next(self.input)

    next = __next__

    def _add_tags(self):
        """Look for headers in the first 25 rows."""
        for n in range(0, 25):
            raw_row = next(self.input)
            if not raw_row:
                break
            self._cache.append(raw_row)
            tag_row = self._try_tag_row(raw_row)
            if tag_row:
                self._cache.append(tag_row)
                return True
        return False

    def _try_tag_row(self, raw_row):
        """See if we can match a header row."""
        tags = []
        tag_count = 0
        for index, value in enumerate(raw_row):
            value = hxl.common.normalise_string(value)
            for spec in self.specs:
                if spec[0] in value:
                    tags.append(spec[1])
                    tag_count += 1
                    break
            else:
                # run only if nothing found
                tags.append('')
        if tag_count > 0 and tag_count/float(len(self.specs)) >= 0.5:
            return tags
        else:
            return None

    def __iter__(self):
        return self

    _SPEC_PATTERN = r'^(.+)(#{token}([+]{token})*)$'.format(token=hxl.common.TOKEN_PATTERN)

    @staticmethod
    def parse_spec(s):
        """Try parsing a tagger spec (used only by the command-line tools)"""
        result = re.match(Tagger._SPEC_PATTERN, s)
        if result:
            return (result.group(1), hxl.model.Column.parse(result.group(2), use_exception=True).display_tag)
        else:
            raise HXLFilterException("Bad tagging spec: " + s)
