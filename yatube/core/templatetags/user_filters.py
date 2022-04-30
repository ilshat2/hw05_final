from django import template
from django.forms import BoundField

register = template.Library()


@register.filter
def addclass(field: BoundField, css: str) -> str:
    """addclass() функция фильтр которая даёт возможность
    указывать CSS-класс в HTML-коде любого поля формы.
    """
    return field.as_widget(attrs={'class': css})
