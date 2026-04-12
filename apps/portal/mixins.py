from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def get_profile(user):
    """Return UserProfile, creating it if missing."""
    from apps.rrhh.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


class PortalLoginMixin(LoginRequiredMixin):
    login_url = '/portal/login/'


class RrhhAccessMixin(PortalLoginMixin):
    """Allows ADMIN, JEFE and SUPERVISOR."""
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response
        profile = get_profile(request.user)
        if not profile.can_see_rrhh:
            raise PermissionDenied
        return response


class AdminAccessMixin(PortalLoginMixin):
    """Only ADMIN."""
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response
        profile = get_profile(request.user)
        if not profile.can_manage_users:
            raise PermissionDenied
        return response
