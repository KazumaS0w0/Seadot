"""
Seadot Auth Middleware (Optional for MVP)
Placeholder untuk authentication dan authorization logic.
Untuk MVP, middleware ini optional - bisa di-enable nanti saat dibutuhkan.
"""


class AuthMiddleware:
    """Simple auth middleware placeholder"""
    
    async def __call__(self, request):
        """Process request through middleware"""
        return request  # Passthrough untuk MVP


async def verify_token(token: str = None) -> bool:
    """Verify JWT token (placeholder)"""
    return True  # No auth for MVP

