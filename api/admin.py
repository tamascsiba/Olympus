from django.contrib import admin
from .models import AllowedCard, CardEvent, AllowedEntry, AllowedExit
from django.utils.timezone import localtime
from django.utils.html import format_html
from django.contrib import admin


@admin.register(AllowedCard)
class AllowedCardAdmin(admin.ModelAdmin):
    list_display = ("uid", "owner_name", "is_allowed")
    list_editable = ("is_allowed",)
    search_fields = ("uid", "owner_name")

@admin.register(CardEvent)
class CardEventAdmin(admin.ModelAdmin):
    list_display = ("reader", "uid", "formatted_timestamp")
    
    def formatted_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    formatted_timestamp.short_description = "Timestamp"

     # Tiltjuk az Add és Change lehetőséget
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(AllowedEntry)
class AllowedEntryAdmin(admin.ModelAdmin):
    list_display = ("uid", "owner_name", "reader", "get_admitted_at")
    readonly_fields = ("uid", "owner_name", "reader", "admitted_at", "original_id")
    ordering = ("-admitted_at",)

    def get_admitted_at(self, obj):
        return localtime(obj.admitted_at).strftime("%Y-%m-%d %H:%M:%S")
    get_admitted_at.short_description = "Admitted At"

     # Tiltjuk az Add és Change lehetőséget
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(AllowedExit)
class AllowedExitAdmin(admin.ModelAdmin):
    list_display = ("uid", "owner_name", "reader", "get_exited_at")
    readonly_fields = ("uid", "owner_name", "reader", "exited_at", "original_id")
    ordering = ("-exited_at",)

    def get_exited_at(self, obj):
        return localtime(obj.exited_at).strftime("%Y-%m-%d %H:%M:%S")
    get_exited_at.short_description = "Exited At"

     # Tiltjuk az Add és Change lehetőséget
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False