from django.urls import path

from . import print_views

urlpatterns = [
    path("prescription/<int:pk>/", print_views.prescription, name="print-prescription"),
    path("sick-note/<int:pk>/", print_views.sick_note, name="print-sick-note"),
    path("referral/<int:pk>/", print_views.referral, name="print-referral"),
]
