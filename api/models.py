from django.db import models
from django.utils import timezone

"""
===============================================================
Django Models – NFC Access Control System
---------------------------------------------------------------
These models store information about NFC card scans, authorized
cards, and entry/exit events detected by the NFC readers.

System logic overview:

Reader 1 → ENTRY reader
Reader 2 → EXIT reader

Workflow:
1. ESP32 reads an NFC card
2. The card UID is sent to the Django API
3. The API checks if the card exists in AllowedCard
4. If the card is allowed:
       - Reader 1 → record entry in AllowedEntry
       - Reader 2 → record exit in AllowedExit
5. Every scan is also logged in CardEvent
===============================================================
"""


class CardEvent(models.Model):
    """
    Stores every NFC scan event received from the ESP32 device.

    This table acts as a raw log of all scans regardless of
    whether the card is authorized or denied.
    """

    reader = models.IntegerField()                  # Which NFC reader detected the card
    uid = models.CharField(max_length=50)           # NFC card UID string
    timestamp = models.DateTimeField(auto_now_add=True)  # Time when the event occurred

    def __str__(self):
        return f"Reader {self.reader} - {self.uid} @ {self.timestamp}"


class AllowedCard(models.Model):
    """
    Stores the list of NFC cards that are authorized
    to access the system.
    """

    uid = models.CharField(max_length=20, unique=True)   # Unique NFC UID
    owner_name = models.CharField(max_length=100, blank=True)  # Optional owner name
    is_allowed = models.BooleanField(default=True)  # True = access granted

    def __str__(self):
        return f"{self.uid} - {'Allowed' if self.is_allowed else 'Denied'}"


class AllowedEntry(models.Model):
    """
    Stores successful ENTRY events.

    Triggered when:
        - Reader 1 detects an allowed card
        - The system grants access
    """

    original_id = models.IntegerField(null=True, blank=True)  
    # ID of the original AllowedCard record

    uid = models.CharField(max_length=64)  
    # UID of the scanned NFC card

    owner_name = models.CharField(max_length=100, blank=True)  
    # Card owner name copied from AllowedCard

    original_is_allowed = models.BooleanField(default=True)  
    # Copy of permission state at the moment of entry

    reader = models.IntegerField()                 
    # Which reader granted entry (typically reader 1)

    admitted_at = models.DateTimeField(auto_now_add=True)  
    # Timestamp when entry occurred

    def __str__(self):
        return f"{self.uid} admitted by reader {self.reader} at {self.admitted_at}"


class AllowedExit(models.Model):
    """
    Stores successful EXIT events.

    Triggered when:
        - Reader 2 detects an allowed card
        - The system grants exit
    """

    original_id = models.IntegerField(null=True, blank=True)
    # ID of the original AllowedCard record

    uid = models.CharField(max_length=64)
    # UID of the scanned NFC card

    owner_name = models.CharField(max_length=100, blank=True)
    # Card owner name copied from AllowedCard

    original_is_allowed = models.BooleanField(default=True)
    # Copy of permission state at the moment of exit

    reader = models.IntegerField()
    # Which reader allowed the exit (typically reader 2)

    exited_at = models.DateTimeField(auto_now_add=True)
    # Timestamp when exit occurred

    def __str__(self):
        return f"{self.uid} exited by reader {self.reader} at {self.exited_at}"