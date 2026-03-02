from django.db import models
from django.utils import timezone

# Create your models here.
class CardEvent(models.Model):
    reader = models.IntegerField()                  # Melyik olvasó
    uid = models.CharField(max_length=50)           # NFC UID string
    timestamp = models.DateTimeField(auto_now_add=True)  # Mikor jött az esemény

    def __str__(self):
        return f"Reader {self.reader} - {self.uid} @ {self.timestamp}"
    

class AllowedCard(models.Model):
    uid = models.CharField(max_length=20, unique=True)
    owner_name = models.CharField(max_length=100, blank=True)
    is_allowed = models.BooleanField(default=True)  # True = beléphet

    def __str__(self):
        return f"{self.uid} - {'Allowed' if self.is_allowed else 'Denied'}"
    
class AllowedEntry(models.Model):
    """Engedélyezett bejövő kártyák (reader 1)"""
    original_id = models.IntegerField(null=True, blank=True)  # eredeti AllowedCard id
    uid = models.CharField(max_length=64)
    owner_name = models.CharField(max_length=100, blank=True)
    original_is_allowed = models.BooleanField(default=True)
    reader = models.IntegerField()                 # melyik reader engedte be (pl. 1)
    admitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.uid} admitted by reader {self.reader} at {self.admitted_at}"

class AllowedExit(models.Model):
    """Engedélyezett kimenő kártyák (reader 2)"""
    original_id = models.IntegerField(null=True, blank=True)
    uid = models.CharField(max_length=64)
    owner_name = models.CharField(max_length=100, blank=True)
    original_is_allowed = models.BooleanField(default=True)
    reader = models.IntegerField()  # melyik reader engedte ki
    exited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.uid} exited by reader {self.reader} at {self.exited_at}"