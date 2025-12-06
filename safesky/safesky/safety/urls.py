from django.urls import path
from . import views

app_name = "safety"

urlpatterns = [
    path("", views.home, name="home"),

    # Tabs
    path("home-tab/", views.home_tab, name="home_tab"),
    path("sos-tab/", views.sos_tab, name="sos_tab"),

    # Chat
    path("secret-chat/", views.secret_chat, name="secret_chat"),
    path('add-contact/', views.add_contact, name='add_contact'),
    path("get-contacts/", views.get_contacts, name="get_contacts"),
    path("send-message/", views.send_chat_message, name="send_chat_message"),
    path('get-messages/<str:contact_username>/', views.get_messages, name='get_messages'),

    # SOS & Notifications
    path("sos/", views.sos, name="sos"),
    path("send-sos/", views.send_sos_alert, name="send_sos"),
    path("notifications/", views.get_notifications, name="get_notifications"),

    # Permissions & Feedback
    path("generate-code/", views.generate_code, name="generate_code"),
    path("send-permission/", views.send_permission, name="send_permission"),
    path("confirm/<uuid:token>/", views.confirm_permission, name="confirm_permission"),
    path("submit-feedback/", views.submit_feedback, name="submit_feedback"),

    # Member tracking (page + json + update)
    path("track/<int:member_id>/", views.track_member, name="track_member"),
    path("track/<int:member_id>/location/", views.get_member_location, name="get_member_location"),
    path("update-location/<int:member_id>/", views.update_location, name="update_location"),

    # Other utility endpoints
    path("get-members-status/", views.get_members_status, name="get_members_status"),
    path("get-members/", views.get_members, name="get_members"),

    path("register/", views.register_view, name="register"),
    path("wait-for-approval/", views.wait_for_approval, name="wait_for_approval"),

    # ADMIN APPROVAL
    path("admin/pending-users/", views.pending_users, name="pending_users"),
    path("admin/approve/<int:user_id>/", views.approve_user, name="approve_user"),

    path("approval-success/", views.approval_success, name="approval_success"),
    path("admin/approvals/", views.admin_approvals, name="admin_approvals"),
]   
 