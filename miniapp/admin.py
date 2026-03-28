from django.contrib import admin
from .models import Item, Tenant, Feedback

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('item', 'tenant', 'rating', 'created_at')
