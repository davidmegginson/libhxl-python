"""
Cut columns from a HXL dataset.
David Megginson
October 2014

Can use a whitelist of HXL tags, a blacklist, or both.

License: Public Domain
Documentation: https://github.com/HXLStandard/libhxl-python/wiki
"""

import sys
import argparse
from hxl.model import HXLDataProvider, HXLRow
from hxl.io import StreamInput, HXLReader, writeHXL
from hxl.filters import TagPattern

class HXLCutFilter(HXLDataProvider):
    """
    Composable filter class to cut columns from a HXL dataset.

    This is the class supporting the hxlcut command-line utility.

    Because this class is a {@link hxl.model.HXLDataProvider}, you can use
    it as the source to an instance of another filter class to build a
    dynamic, single-threaded processing pipeline.

    Usage:

    <pre>
    source = HXLReader(sys.stdin)
    filter = HXLCutFilter(source, include_tags=['#sector', '#org', '#adm1'])
    writeHXL(sys.stdout, filter)
    </pre>
    """

    def __init__(self, source, include_tags=[], exclude_tags=[]):
        """
        @param source a HXL data source
        @param include_tags a whitelist list of hashtags to include
        @param exclude_tags a blacklist of hashtags to exclude
        """
        self.source = source
        self.include_tags = include_tags
        self.exclude_tags = exclude_tags
        self.indices = [] # saved indices for columns to include
        self.columns_out = None

    @property
    def columns(self):
        """
        Filter out the columns that should be removed.
        """
        if self.columns_out is None:
            self.columns_out = []
            columns = self.source.columns
            for i in range(len(columns)):
                column = columns[i]
                if self._test_column(column):
                    self.columns_out.append(column)
                    self.indices.append(i) # save index to avoid retesting for data
        return self.columns_out

    def __next__(self):
        """
        Return the next row, with appropriate columns filtered out.
        """
        row_in = next(self.source)
        row_out = HXLRow(columns=self.columns)
        values_out = []
        for i in self.indices:
            values_out.append(row_in.values[i])
        row_out.values = values_out
        return row_out

    next = __next__

    def _test_column(self, column):
        """
        Test whether a column should be included in the output.
        If there is a whitelist, it must be in the whitelist; if there is a blacklist, it must not be in the blacklist.
        """
        if self.exclude_tags:
            # blacklist
            for pattern in self.exclude_tags:
                if pattern.match(column):
                    # fail as soon as we match an excluded pattern
                    return False

        if self.include_tags:
            # whitelist
            for pattern in self.include_tags:
                if pattern.match(column):
                    # succeed as soon as we match an included pattern
                    return True
            # fail if there was a whitelist and we didn't match
            return False
        else:
            # no whitelist
            return True

#
# Command-line support
#

def run(args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    """
    Run hxlcut with command-line arguments.
    @param args A list of arguments, excluding the script name
    @param stdin Standard input for the script
    @param stdout Standard output for the script
    @param stderr Standard error for the script
    """

    parser = argparse.ArgumentParser(description = 'Cut columns from a HXL dataset.')
    parser.add_argument(
        'infile',
        help='HXL file to read (if omitted, use standard input).',
        nargs='?',
        type=argparse.FileType('r'),
        default=stdin
        )
    parser.add_argument(
        'outfile',
        help='HXL file to write (if omitted, use standard output).',
        nargs='?',
        type=argparse.FileType('w'),
        default=stdout
        )
    parser.add_argument(
        '-i',
        '--include',
        help='Comma-separated list of column tags to include',
        metavar='tag,tag...',
        type=TagPattern.parse_list
        )
    parser.add_argument(
        '-x',
        '--exclude',
        help='Comma-separated list of column tags to exclude',
        metavar='tag,tag...',
        type=TagPattern.parse_list
        )
    args = parser.parse_args(args)

    with args.infile, args.outfile:
        source = HXLReader(StreamInput(args.infile))
        filter = HXLCutFilter(source, args.include, args.exclude)
        writeHXL(args.outfile, filter)

# end
