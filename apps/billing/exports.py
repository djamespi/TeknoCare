"""File formatting for the prototype Pending-charge export."""
import csv
import unicodedata

from django.http import HttpResponse


def _spreadsheet_text(value):
    text = str(value).translate(str.maketrans({"\r": " ", "\n": " ", "\t": " "}))
    candidate = unicodedata.normalize("NFKC", text)
    candidate = candidate.lstrip(" '\"\ufeff\u200b\u2060")
    if candidate.startswith(("=", "+", "-", "@")):
        return f"Text: {text}"
    return text


def pending_csv(charges):
    response = HttpResponse(content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="teknocare-pending-tuition-demo.csv"'})
    writer = csv.writer(response, quoting=csv.QUOTE_ALL)
    writer.writerow(["charge_code", "student_id", "academic_year", "semester", "description", "amount", "currency"])
    rows = charges.values_list("charge_code", "record__patient__patient__school_id", "term__academic_year",
        "term__semester", "description", "amount", "currency_code")
    for code, school_id, year, semester, description, amount, currency in rows.iterator():
        writer.writerow([*map(_spreadsheet_text, (code, school_id, year, semester, description)), format(amount, ".2f"), currency])
    return response
