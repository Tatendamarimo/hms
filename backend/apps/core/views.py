from django.db import connection
from django.http import JsonResponse


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")  # noqa: S608 — constant health probe, not data access
    return JsonResponse({"status": "ok"})
