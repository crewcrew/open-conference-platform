from .models import AuditLog


def record(organization, actor, action, summary, *, event=None, obj=None, changes=None):
    return AuditLog.objects.create(
        organization=organization,
        event=event,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        object_type=obj.__class__.__name__ if obj is not None else "",
        object_id=str(obj.pk) if obj is not None else "",
        summary=summary,
        changes=changes or {},
    )


def diff(instance, form):
    """Field changes from a bound ModelForm, as {field: [old, new]} strings."""
    changes = {}
    for name in form.changed_data:
        old = form.initial.get(name)
        new = form.cleaned_data.get(name)
        changes[name] = [_text(old), _text(new)]
    return changes


def _text(value):
    if value is None:
        return ""
    if hasattr(value, "all"):
        return ", ".join(str(item) for item in value.all())
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item) for item in value)
    return str(value)
