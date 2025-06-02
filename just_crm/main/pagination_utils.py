from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def get_paginated_objects(request, objects, per_page):
    paginator = Paginator(objects, per_page)
    page = request.GET.get('page')

    try:
        paginated_objects = paginator.page(page)
    except PageNotAnInteger:
        paginated_objects = paginator.page(1)
    except EmptyPage:
        paginated_objects = paginator.page(paginator.num_pages)

    return paginated_objects