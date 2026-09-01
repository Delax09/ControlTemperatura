from rest_framework import filters, viewsets


class BaseCrudViewSet(viewsets.ModelViewSet):
    """
    Base común del CRUD de cada tabla.

    Aporta búsqueda (?search=) y ordenamiento (?ordering=) sin dependencias
    extra: solo los filtros que trae DRF. Cada módulo define su queryset,
    su serializer y qué campos son buscables/ordenables.
    """

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = []
    ordering_fields = '__all__'
