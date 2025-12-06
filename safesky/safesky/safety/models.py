from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class SecretChatContact(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_contacts", null=True, blank=True)
    username = models.CharField(max_length=150)
    contact_username = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("username", "contact_username")
        verbose_name = "Secret Chat Contact"
        verbose_name_plural = "Secret Chat Contacts"

    def __str__(self):
        return f"{self.username} ↔ {self.contact_username}"

    @staticmethod
    def get_or_create_contact(username, contact_username, user=None):
        contact1, _ = SecretChatContact.objects.get_or_create(
            username=username,
            contact_username=contact_username,
            defaults={"user": user},
        )
        contact2, _ = SecretChatContact.objects.get_or_create(
            username=contact_username,
            contact_username=username,
            defaults={"user": user},
        )
        return contact1


class SecretMessage(models.Model):
    sender_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_local_messages",
                                    null=True, blank=True)
    receiver_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_local_messages",
                                      null=True, blank=True)
    sender_name = models.CharField(max_length=150)
    receiver_name = models.CharField(max_length=150)
    content = models.TextField(blank=True)
    file = models.FileField(upload_to="chat_files/", blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        preview = (self.content[:25] + "...") if len(self.content) > 25 else self.content
        return f"{self.sender_name} → {self.receiver_name}: {preview}"

    def save(self, *args, **kwargs):
        if self.sender_user and not self.sender_name:
            self.sender_name = self.sender_user.username
        if self.receiver_user and not self.receiver_name:
            self.receiver_name = self.receiver_user.username

        SecretChatContact.get_or_create_contact(self.sender_name, self.receiver_name, self.sender_user)
        SecretChatContact.get_or_create_contact(self.receiver_name, self.sender_name, self.receiver_user)

        super().save(*args, **kwargs)


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(default="")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        user_name = self.user.username if self.user else "Guest"
        return f"Notification for {user_name}"


class PermissionRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    )

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_requests', null=True, blank=True)
    recipient_email = models.EmailField()
    code_hash = models.CharField(max_length=128, default="")
    display_code = models.CharField(max_length=20, blank=True, default="")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        requester_name = self.requester.username if self.requester else "Guest"
        return f"{requester_name} → {self.recipient_email} ({self.status})"


class MemberLocation(models.Model):
    """
    Stores the latest location for a member (one-to-one with User).
    Update this from devices or admin to change the tracked position.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

# models.py  register
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=10)
    is_approved = models.BooleanField(default=False)
    # created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


from django.db.models.signals import post_save
from django.dispatch import receiver
