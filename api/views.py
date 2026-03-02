from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import CardEvent, AllowedCard, AllowedEntry, AllowedExit
from .serializers import CardEventSerializer
from django.db import transaction

@api_view(["POST"])
def card_event(request):
    serializer = CardEventSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()  # mentés DB-be
        return Response({"message": "OK", "saved": serializer.data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
def list_events(request):
    events = CardEvent.objects.order_by("-timestamp")
    serializer = CardEventSerializer(events, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def check_card(request):
    uid = request.data.get('uid')
    reader = request.data.get('reader')

    if not uid:
        return Response({"action": "DENIED", "message": "UID missing"}, status=400)

    uid_clean = uid.strip().upper()

    try:
        card = AllowedCard.objects.get(uid=uid_clean)
        allowed = bool(card.is_allowed)
    except AllowedCard.DoesNotExist:
        allowed = False
        card = None

    # Naplózás minden próbálkozásról
    CardEvent.objects.create(reader=reader, uid=uid_clean)

    # Engedélyezett kártya feldolgozása
    if allowed and card is not None:
        try:
            with transaction.atomic():
                if reader == 1:
                    # Beengedett kártya, csak másoljuk
                    AllowedEntry.objects.create(
                        original_id=card.id,
                        uid=card.uid,
                        owner_name=card.owner_name,
                        original_is_allowed=card.is_allowed,
                        reader=reader
                    )
                    return Response({"action": "GATE_OPEN"})
                elif reader == 2:
                    # Kimenő kártya, csak másoljuk
                    AllowedExit.objects.create(
                        original_id=card.id,
                        uid=card.uid,
                        owner_name=card.owner_name,
                        original_is_allowed=card.is_allowed,
                        reader=reader
                    )
                    return Response({"action": "GATE_OPEN"})
        except Exception as e:
            return Response({"action": "DENIED", "message": "Server error during transfer"}, status=500)

    # Alapértelmezett: tiltás
    return Response({"action": "DENIED"})


