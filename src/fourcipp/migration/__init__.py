# The MIT License (MIT)
#
# Copyright (c) 2025 FourCIPP Authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""Optional tool to migrate 4C input files across `input_version` bumps.

This is entirely opt-in: 4C's `input_version` field is not required, and input files
without it (or that are never migrated) continue to work as before. See
`fourcipp.migration.migrator` for the main entry points, `migrate_sections` and
`migrate_file`.
"""

from fourcipp.migration.errors import MigrationError
from fourcipp.migration.migrator import MigrationReport, migrate_file, migrate_sections

__all__ = [
    "MigrationError",
    "MigrationReport",
    "migrate_file",
    "migrate_sections",
]
