"""
Cut columns from a HXL dataset.
David Megginson
October 2014

Can use a whitelist of HXL tags, a blacklist, or both.

License: Public Domain
Documentation: https://github.com/HXLStandard/libhxl-python/wiki
"""

from hxl.model import Dataset, Row
from hxl.io import HXLReader, write_hxl
from hxl.common import pattern_list

class ColumnFilter(Dataset):
    """
    Composable filter class to cut columns from a HXL dataset.

    This is the class supporting the hxlcut command-line utility.

    Because this class is a {@link hxl.model.Dataset}, you can use
    it as the source to an instance of another filter class to build a
    dynamic, single-threaded processing pipeline.

    Usage:

    <pre>
    filter = ColumnFilter(source, include_tags=['#org', '#sector', '#adm1'])
    write_hxl(sys.stdout, filter)
    </pre>
    """

    def __init__(self, source, include_tags=[], exclude_tags=[]):
        """
        @param source a HXL data source
        @param include_tags a whitelist of TagPattern objects to include
        @param exclude_tags a blacklist of TagPattern objects to exclude
        """
        self.source = source
        self.include_tags = pattern_list(include_tags)
        self.exclude_tags = pattern_list(exclude_tags)
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

    def __iter__(self):
        return ColumnFilter.Iterator(self)

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

    class Iterator:

        def __init__(self, outer):
            self.outer = outer
            self.iterator = iter(outer.source)

        def __next__(self):
            """
            Return the next row, with appropriate columns filtered out.
            """
            row_in = next(self.iterator)
            row_out = Row(columns=self.outer.columns)
            values_out = []
            for i in self.outer.indices:
                values_out.append(row_in.values[i])
            row_out.values = values_out
            return row_out

        next = __next__

# end