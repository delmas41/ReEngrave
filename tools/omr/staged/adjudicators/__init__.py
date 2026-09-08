"""One module per decision. Importing this package populates the registry.

⚠️ EVERY quantity in `adjudicate.ORDER` must have an owner here, even if that
owner is a declared stub. A stub is fine; a MISSING decision is not, because
a missing decision is indistinguishable from one that always abstains and
nobody can tell which they are looking at.
"""

from . import structure   # noqa: F401
from . import identity    # noqa: F401
from . import clef        # noqa: F401
from . import header      # noqa: F401
from . import ownership   # noqa: F401
from . import rhythm      # noqa: F401
from . import text        # noqa: F401
