from django import template
from django.http import QueryDict

register = template.Library()


@register.simple_tag(takes_context=True)
def pagination_url(context, page_number):
    request = context.get("request")
    query = request.GET.copy() if request else QueryDict(mutable=True)
    query["page"] = str(page_number)
    return f"?{query.urlencode()}"
