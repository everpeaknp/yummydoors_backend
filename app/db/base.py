import app.modules.catalog.models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.customers.models  # noqa: F401
import app.modules.integrations.pos.models  # noqa: F401
import app.modules.merchandising.models  # noqa: F401
import app.modules.restaurants.models  # noqa: F401
import app.modules.workspaces.models  # noqa: F401
import app.modules.carts.models  # noqa: F401
import app.modules.orders.models  # noqa: F401
import app.modules.reservations.models  # noqa: F401
import app.modules.favorites.models  # noqa: F401
import app.modules.messages.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.rider_applications.models  # noqa: F401
import app.modules.rider_dispatch.models  # noqa: F401

from app.db.session import Base

__all__ = ["Base"]
