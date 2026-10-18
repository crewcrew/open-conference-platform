from django.utils.text import slugify

from django import forms

DATETIME_WIDGET = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
DATE_WIDGET = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")

def unique_slug(model, base, field="slug"):
    base = slugify(base)[:60] or "item"
    slug, n = base, 2
    while model.objects.filter(**{field: slug}).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug
