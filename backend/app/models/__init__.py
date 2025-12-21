# Import models in correct order (dependencies matter!)

# 1. Independent models (no foreign keys to other models)
from app.models.role import Role

# 2. Organization (independent)
from app.models.user import Organization, User

# 3. Site (depends on Organization)
from app.models.site import Site

# 4. Worker (depends on Organization, Site, User)
from app.models.worker import Worker

# 5. Device and ClockEvent
from app.models.event import Device, ClockEvent

# 6. Junction table
from app.models.user_site import UserSite

# 7. Checkpoint (depends on Site, User)
from app.models.checkpoint import Checkpoint


# Export all models
__all__ = [
    # Core entities
    "Organization",
    "User",
    "Site",
    "Worker",
    "Device",
    "ClockEvent",
    
    # Junction tables
    "UserSite",
    
    # ✅ NEW in STAGE 1
    "Role",
    "Checkpoint",
]