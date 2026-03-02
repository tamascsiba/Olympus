from django.urls import path
from . import views

urlpatterns = [
    path("card/", views.card_event, name="card_event"),
    path("events/", views.list_events, name="list_events"),  # GET a legutóbbi eseményekhez
    path('check_card/', views.check_card, name='check_card'),

]