from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import UserProfile

from django.contrib.auth.decorators import user_passes_test
from .models import UserProfile


import json
import random
import secrets
import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace

from .models import (
    MemberLocation,
    SecretChatContact,
    SecretMessage,
    Notification,
    PermissionRequest,
)

# Optional Member model
try:
    from .models import Member
    HAVE_MEMBER = True
except Exception:
    Member = None
    HAVE_MEMBER = False

User = get_user_model()

# ---------------- DEMO fallback coordinates ----------------
MEMBER_LOCATIONS = {
    1: {"lat": 28.6139, "lng": 77.2090, "name": "Divyansh"},  # Delhi
    2: {"lat": 19.0760, "lng": 72.8777, "name": "Bhavya"},    # Mumbai
    3: {"lat": 26.9124, "lng": 75.7873, "name": "Shivang"},   # Jaipur
    4: {"lat": 28.7041, "lng": 77.1025, "name": "Ansh"},      # Delhi (random)
}


# ---------------- MEMBER LIST ----------------
def get_members_status(request):
    """Static members for demo display."""
    MEMBERS = [
        {
            "id": 1,
            "name": "Divyansh",
            "status": "granted",
            "status_label": "Permission Granted",
        },
        {
            "id": 2,
            "name": "Bhavya",
            "status": "granted",     # ✅ Activated
            "status_label": "Permission Granted",
        },
        {
            "id": 3,
            "name": "Shivang",
            "status": "denied",
            "status_label": "Access Denied",
        },
        {
            "id": 4,
            "name": "Ansh",
            "status": "pending",     # ✅ Newly added
            "status_label": "Pending Verification",
        },
    ]

    return JsonResponse({"members": MEMBERS})


def get_members(request):
    """Return all registered users with their location status."""
    users = User.objects.all().order_by("id")
    out = []
    for u in users:
        try:
            loc = MemberLocation.objects.get(user=u)
            has_location = loc.latitude is not None and loc.longitude is not None
        except MemberLocation.DoesNotExist:
            has_location = False
        out.append({
            "id": u.id,
            "username": u.username,
            "email": getattr(u, "email", ""),
            "has_location": has_location,
        })
    return JsonResponse({"members": out})


# ---------------- LOCATION TRACKING ----------------
def _resolve_member_and_location(member_id):
    # 1️⃣ FIRST: Check DEMO data
    if member_id in MEMBER_LOCATIONS:
        loc = MEMBER_LOCATIONS[member_id]
        return loc["name"], loc["lat"], loc["lng"]

    # 2️⃣ SECOND: Check real MemberLocation
    try:
        loc_obj = MemberLocation.objects.get(id=member_id)
        username = loc_obj.user.username
        return username, float(loc_obj.latitude), float(loc_obj.longitude)
    except MemberLocation.DoesNotExist:
        pass

    # 3️⃣ THIRD: Check real User
    try:
        user = User.objects.get(id=member_id)
        loc_obj = MemberLocation.objects.filter(user=user).first()
        if loc_obj:
            return user.username, float(loc_obj.latitude), float(loc_obj.longitude)
        return user.username, None, None
    except User.DoesNotExist:
        return None, None, None


def track_member(request, member_id):
    """Render the map tracking page for a member."""
    username, lat, lng = _resolve_member_and_location(member_id)
    if username is None:
        return HttpResponse("Member not found", status=404)

    member = SimpleNamespace(username=username, id=member_id, latitude=lat, longitude=lng)
    return render(request, "safety/track_member.html", {"member": member})


@require_GET
def get_member_location(request, member_id):
    """Return member’s coordinates."""
    username, lat, lng = _resolve_member_and_location(member_id)
    if username is None:
        return JsonResponse({"error": "Member not found"}, status=404)

    if lat is not None and lng is not None:
        return JsonResponse({"lat": lat, "lng": lng, "name": username})

    # fallback
    loc = MEMBER_LOCATIONS.get(member_id)
    if loc:
        return JsonResponse({"lat": loc["lat"], "lng": loc["lng"], "name": loc["name"]})

    # simulate location near Delhi
    sim_lat = 28.4522 + random.uniform(-0.02, 0.02)
    sim_lng = 77.0571 + random.uniform(-0.02, 0.02)
    return JsonResponse({"lat": sim_lat, "lng": sim_lng, "name": username})


@csrf_exempt
@require_POST
def update_location(request, member_id):
    """Accept user’s live location updates."""
    try:
        if "application/json" in request.content_type:
            payload = json.loads(request.body.decode("utf-8"))
            lat = float(payload.get("lat"))
            lng = float(payload.get("lng"))
        else:
            lat = float(request.POST.get("lat"))
            lng = float(request.POST.get("lng"))
    except Exception:
        return JsonResponse({"error": "Invalid payload; expected lat & lng"}, status=400)

    try:
        user = User.objects.get(id=member_id)
        loc_obj, _ = MemberLocation.objects.get_or_create(user=user)
        loc_obj.latitude = lat
        loc_obj.longitude = lng
        loc_obj.updated_at = timezone.now()
        loc_obj.save(update_fields=["latitude", "longitude", "updated_at"])
        return JsonResponse({"status": "ok", "lat": lat, "lng": lng})
    except User.DoesNotExist:
        MEMBER_LOCATIONS[member_id] = {"lat": lat, "lng": lng}
        return JsonResponse({"status": "ok", "lat": lat, "lng": lng})


# ---------------- BASIC PAGES ----------------
def home(request):
    return render(request, "safety/home.html")


def home_tab(request):
    """Main home tab — list members + buttons."""
    have_member = HAVE_MEMBER and Member.objects.exists()
    members = Member.objects.all().order_by("-id") if have_member else []
    return render(request, "safety/home_tab.html", {"members": members, "have_member": have_member})


def sos_tab(request):
    return render(request, "safety/sos_tab.html")


def sos(request):
    return render(request, "safety/sos.html")


# ---------------- SECRET CHAT ----------------
def secret_chat(request):
    username = request.user.username if request.user.is_authenticated else request.GET.get("username", "Guest")
    contacts = SecretChatContact.objects.filter(username=username).order_by("-created_at")
    return render(request, "safety/secret_chat.html", {"username": username, "contacts": contacts})


def get_messages(request, contact_username):
    username = request.GET.get('username')
    try:
        user = User.objects.get(username=username)
        contact = User.objects.get(username=contact_username)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    messages = SecretChatMessage.objects.filter(
        sender__in=[user, contact],
        receiver__in=[user, contact]
    ).order_by('timestamp')

    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'sender': msg.sender.username,
            'receiver': msg.receiver.username,
            'message': msg.message,
            'file': msg.file.url if msg.file else None,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return JsonResponse({'messages': data})


@require_POST
def add_contact(request):
    """
    Add a new contact for chatting. Works for both logged-in and local users.
    """
    username = request.POST.get("username")
    contact_username = request.POST.get("contact_username")

    if not username or not contact_username:
        return JsonResponse({"success": False, "error": "Both usernames required"})

    try:
        SecretChatContact.get_or_create_contact(
            username=username,
            contact_username=contact_username,
            user=request.user if request.user.is_authenticated else None
        )
        return JsonResponse({"success": True, "message": f"Contact '{contact_username}' added"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@csrf_exempt
@require_POST
def send_chat_message(request):
    username = request.user.username if request.user.is_authenticated else request.POST.get("username", "Guest")
    contact_name = request.POST.get("contact_name", "").strip()
    message = request.POST.get("message", "").strip()
    file = request.FILES.get("file")

    if not contact_name:
        return JsonResponse({"error": "Missing contact name"}, status=400)
    if not message and not file:
        return JsonResponse({"error": "Message or file required"}, status=400)

    sender_user = User.objects.filter(username=username).first()
    receiver_user = User.objects.filter(username=contact_name).first()

    SecretChatContact.get_or_create_contact(username=username, contact_username=contact_name, user=sender_user)
    SecretChatContact.get_or_create_contact(username=contact_name, contact_username=username, user=receiver_user)

    msg = SecretMessage.objects.create(
        sender_user=sender_user,
        receiver_user=receiver_user,
        sender_name=username,
        receiver_name=contact_name,
        content=message or "",
        file=file if file else None,
    )

    return JsonResponse({
        "status": "success",
        "sender": msg.sender_name,
        "content": msg.content,
        "file_url": msg.file.url if msg.file else None,
        "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    })


@require_GET
def get_contacts(request):
    owner = request.GET.get("owner") or (request.user.username if request.user.is_authenticated else "Guest")
    contacts = SecretChatContact.objects.filter(username=owner).order_by("-created_at")
    data = [{
        "id": c.id,
        "username": c.username,
        "contact_username": c.contact_username,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for c in contacts]
    return JsonResponse({"contacts": data})


# ---------------- SOS & NOTIFICATIONS ----------------
def send_sos_alert(request):
    user_name = request.user.username if request.user.is_authenticated else "Guest"
    message = f"{user_name} sent an SOS! Please check immediately."
    for contact in User.objects.all():
        Notification.objects.create(user=contact, message=message)
    return render(request, "safety/sos_alert.html", {"message": "SOS Sent!"})


def get_notifications(request):
    if not request.user.is_authenticated:
        return JsonResponse({"new_notifications": []})
    new_notifications = Notification.objects.filter(user=request.user, is_read=False)
    notifications = [{"message": n.message} for n in new_notifications]
    new_notifications.update(is_read=True)
    return JsonResponse({"new_notifications": notifications})


# ---------------- PERMISSION SYSTEM ----------------
CODE_EXPIRY_MINUTES = getattr(settings, "SAFESKY_CODE_EXPIRY_MINUTES", 10)

from datetime import datetime, timedelta, timezone

@csrf_exempt
@require_POST
def generate_code(request):
    try:
        raw_code = secrets.token_urlsafe(6)
        display_code = raw_code[:8]
        code_hash = hashlib.sha256(display_code.encode("utf-8")).hexdigest()

        # ✅ FIXED: use Python's timezone.utc
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)

        requester = request.user if getattr(request, "user", None) and request.user.is_authenticated else None

        pr = PermissionRequest.objects.create(
            requester=requester,
            code_hash=code_hash,
            display_code=display_code,
            expires_at=expires_at,
            status="pending",
        )

        return JsonResponse({
            "display_code": display_code,
            "request_id": pr.id,
            "expires_at": expires_at.isoformat()
        })

    except Exception as e:
        return JsonResponse({"error": f"Failed to generate code: {e}"}, status=500)


@csrf_exempt  # ✅ also make this easy for JS
@require_POST
def send_permission(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        code = data.get("code", "").strip()
        email = data.get("recipient_email", "").strip()
    except Exception:
        return JsonResponse({"error": "Invalid payload"}, status=400)

    if not code or not email:
        return JsonResponse({"error": "Missing code or email"}, status=400)

    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    pr = PermissionRequest.objects.filter(code_hash=code_hash, status="pending", expires_at__gt=now).first()
    if not pr:
        return JsonResponse({"error": "Invalid or expired code"}, status=400)

    pr.recipient_email = email
    pr.save()
    domain = request.get_host()
    path = reverse("safety:confirm_permission", kwargs={"token": str(pr.token)})
    url = f"{request.scheme}://{domain}{path}"
    return JsonResponse({"message": f"Permission sent: {url}"})


@require_GET
def confirm_permission(request, token):
    pr = get_object_or_404(PermissionRequest, token=token)
    now = datetime.now(timezone.utc)
    if pr.expires_at and pr.expires_at < now:
        pr.status = "expired"
        pr.save()
        return HttpResponse("This permission link has expired.")
    pr.status = "accepted"
    pr.confirmed_at = now
    pr.save()

    if HAVE_MEMBER and pr.recipient_email:
        member, created = Member.objects.get_or_create(email=pr.recipient_email, defaults={
            "display_name": pr.recipient_email.split("@")[0],
            "permission_status": "granted",
        })
        if not created:
            member.permission_status = "granted"
            member.save(update_fields=["permission_status"])
    return HttpResponse("Permission confirmed. You can now be tracked.")


# ---------------- FEEDBACK ----------------
@csrf_exempt
def submit_feedback(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            feedback = data.get("feedback", "")
            if not feedback:
                return JsonResponse({"message": "Feedback cannot be empty."}, status=400)
            # TODO: save feedback later
            return JsonResponse({"message": "Thank you for your feedback!"})
        except Exception as e:
            return JsonResponse({"message": f"Error: {e}"}, status=500)
    return JsonResponse({"message": "Invalid request."}, status=400)
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from .models import UserProfile
from django.http import HttpResponse


def register_view(request):

    if request.method == "POST":
        name = request.POST.get("full_name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm = request.POST.get("cpassword")

        if password != confirm:
            return render(request, "registration/register.html", {"error": "Passwords do not match"})

        if User.objects.filter(username=email).exists():
            return render(request, "registration/register.html", {"error": "User already exists"})

        # Create user
        user = User.objects.create_user(username=email, email=email, password=password)
        user.first_name = name
        user.save()

        # Create pending profile
        profile = UserProfile.objects.create(
            user=user,
            phone=phone,
            is_approved=False
        )

        print("PROFILE CREATED:", profile)

        # Auto-login the user
        login(request, user)

        return redirect("wait_for_approval")

    return render(request, "registration/register.html")

def pending_users(request):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)

    pending = UserProfile.objects.filter(is_approved=False)
    return render(request, "admin/pending_users.html", {"pending": pending})

def approval_success(request):
    return render(request, "registration/approval_success.html")


@user_passes_test(lambda u: u.is_superuser)
def admin_approvals(request):
    pending = UserProfile.objects.filter(is_approved=False)
    return render(request, "registration/admin_approvals.html", {"pending": pending})

def wait_for_approval(request):
    return render(request, "registration/wait_for_approval.html")

def approve_user(request, user_id):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)

    profile = get_object_or_404(UserProfile, id=user_id)
    profile.is_approved = True
    profile.save()

    return redirect("safety:admin_approvals")