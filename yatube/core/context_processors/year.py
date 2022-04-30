from datetime import date

from django.core.handlers.wsgi import WSGIRequest


def year(request: WSGIRequest) -> dict:
    """Функция year возвращающая текущий год,
    отображается в подвале страницы.
    """
    year = date.today().year
    context = {'year': year}
    return context
