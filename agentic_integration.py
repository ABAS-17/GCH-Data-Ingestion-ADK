# Import and add user management router
from data.api.user_endpoints import router as user_router
app.include_router(user_router)

# Import and add agentic layer router
from data.api.agentic_endpoints import router as agentic_router
app.include_router(agentic_router)
