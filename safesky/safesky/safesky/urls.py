from django.contrib import admin
from django.urls import path, include
from weather import views  # import your weather app views
from django.contrib.auth import views as auth_views
from safety.views import register_view, wait_for_approval

urlpatterns = [
    path('admin/', admin.site.urls),

    # Home page (weather app)
    path('', views.home, name='weather-home'),

    # Safety app (with namespace)
    path('safety/', include(('safety.urls', 'safety'), namespace='safety')),

    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
     path("register/", register_view, name="register"),
    path("wait-for-approval/", wait_for_approval, name="wait_for_approval"),
]

