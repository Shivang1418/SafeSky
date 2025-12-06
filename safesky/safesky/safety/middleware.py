from django.shortcuts import redirect
from .models import UserProfile

class SafeSkyAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # --- Allow these pages without approval/login ---
        allowed_paths = [
            "/register",
            "/wait-for-approval",
            "/accounts/login/",
            "/static/",
        ]

        # Allow admin approval page
        if path.startswith("/safety/admin/"):
            return self.get_response(request)

        # Skip allowed pages
        if any(path.startswith(p) for p in allowed_paths):
            return self.get_response(request)

        # Apply protection only on safety app pages
        if path.startswith("/safety"):

            # User not logged in → send to register
            if not request.user.is_authenticated:
                return redirect("register")

            # Fetch profile
            try:
                profile = UserProfile.objects.get(user=request.user)
            except UserProfile.DoesNotExist:
                return redirect("register")

            # Not approved → show waiting page
            if not profile.is_approved:
                return redirect("wait_for_approval")

        return self.get_response(request)
