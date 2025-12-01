from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog

class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to log critical actions"""
    
    def process_response(self, request, response):
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Log login/logout
            if request.path == '/accounts/login/' and response.status_code == 302:
                AuditLog.log(
                    user=request.user,
                    action=AuditLog.Action.LOGIN,
                    description=f"User {request.user.username} logged in",
                    ip_address=self.get_client_ip(request)
                )
        return response
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip