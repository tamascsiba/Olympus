from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import CardEvent, AllowedCard, AllowedEntry, AllowedExit
from .serializers import CardEventSerializer
from django.db import transaction


"""
=================================================================
Django REST API – NFC Access Control System
-----------------------------------------------------------------
This API receives NFC card scans from an ESP32 device and decides
whether access should be granted.

Workflow:
1. ESP32 reads an NFC card
2. ESP32 sends UID + reader number via HTTP POST
3. Django checks if the card exists in AllowedCard
4. If allowed:
      - Reader 1 → record entry in AllowedEntry
      - Reader 2 → record exit in AllowedExit
5. Every scan is logged in CardEvent
6. API returns response to ESP32:
      { "action": "GATE_OPEN" } or { "action": "DENIED" }
=================================================================
"""


@api_view(["POST"])
def card_event(request):
    """
    Endpoint: /api/card_event/

    Saves a raw card scan event to the database.

    This endpoint stores incoming scan events without checking
    access permissions. Mainly used for logging and debugging.
    """

    serializer = CardEventSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()  # Save event to database
        return Response(
            {"message": "OK", "saved": serializer.data},
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def list_events(request):
    """
    Endpoint: /api/list_events/

    Returns a list of all NFC scan events ordered by time
    (newest first).
    """

    events = CardEvent.objects.order_by("-timestamp")
    serializer = CardEventSerializer(events, many=True)

    return Response(serializer.data)


@api_view(['POST'])
def check_card(request):
    """
    Endpoint: /api/check_card/

    Main access control endpoint used by the ESP32.

    Expected JSON input:
    {
        "reader": 1,
        "uid": "04:A3:12:BC"
    }

    Logic:
    - Check if card UID exists in AllowedCard
    - Verify permission (is_allowed)
    - Log every scan attempt
    - If allowed:
          Reader 1 → create AllowedEntry
          Reader 2 → create AllowedExit
    - Return access decision to ESP32
    """

    uid = request.data.get('uid')
    reader = request.data.get('reader')

    # Validate UID
    if not uid:
        return Response(
            {"action": "DENIED", "message": "UID missing"},
            status=400
        )

    # Normalize UID format
    uid_clean = uid.strip().upper()

    # Check if card exists in allowed list
    try:
        card = AllowedCard.objects.get(uid=uid_clean)
        allowed = bool(card.is_allowed)
    except AllowedCard.DoesNotExist:
        allowed = False
        card = None

    # Log every scan attempt
    CardEvent.objects.create(reader=reader, uid=uid_clean)

    # Process authorized cards
    if allowed and card is not None:
        try:
            with transaction.atomic():

                if reader == 1:
                    # ENTRY reader
                    AllowedEntry.objects.create(
                        original_id=card.id,
                        uid=card.uid,
                        owner_name=card.owner_name,
                        original_is_allowed=card.is_allowed,
                        reader=reader
                    )

                    return Response({"action": "GATE_OPEN"})


                elif reader == 2:
                    # EXIT reader
                    AllowedExit.objects.create(
                        original_id=card.id,
                        uid=card.uid,
                        owner_name=card.owner_name,
                        original_is_allowed=card.is_allowed,
                        reader=reader
                    )

                    return Response({"action": "GATE_OPEN"})

        except Exception:
            return Response(
                {
                    "action": "DENIED",
                    "message": "Server error during transfer"
                },
                status=500
            )

    # Default response if access is denied
    return Response({"action": "DENIED"})