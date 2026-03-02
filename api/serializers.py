from rest_framework import serializers
from .models import CardEvent, AllowedEntry, AllowedExit
from django.utils import timezone

class CardEventSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S", 
        default_timezone=timezone.get_current_timezone())

    class Meta:
        model = CardEvent
        fields = "__all__"

class AllowedEntrySerializer(serializers.ModelSerializer):
    admitted_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        default_timezone=timezone.get_current_timezone()
    )

    class Meta:
        model = AllowedEntry
        fields = "__all__"

class AllowedExitSerializer(serializers.ModelSerializer):
    exited_at = serializers.DateTimeField(
        format="%Y-%m-%d %H:%M:%S",
        default_timezone=timezone.get_current_timezone()
    )

    class Meta:
        model = AllowedExit
        fields = "__all__"