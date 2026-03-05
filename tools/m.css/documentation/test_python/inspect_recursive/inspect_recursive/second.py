"""Second module, imported as inspect_recursive.a, with no contents"""

import sys

if sys.version_info >= (3, 7):
    # For some reason 3.6 says second doesn't exist yet. I get that, it's a
    # cyclic reference, but that works in 3.7.
    pass

from inspect_recursive import Foo as Bar
