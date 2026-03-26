from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'rating', 'is_resolved', 'created_at')
    list_filter = ('rating', 'is_resolved')
