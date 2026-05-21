# Pagination classes for DRF views
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsPagination(PageNumberPagination):
    page_size            = 12
    page_size_query_param = "page_size"
    max_page_size        = 100
    page_query_param     = "page"

    def get_paginated_response(self, data):
        return Response({
            "count":    self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "next":     self.get_next_link(),
            "previous": self.get_previous_link(),
            "results":  data,
        })

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "results"],
            "properties": {
                "count":       {"type": "integer", "example": 42},
                "total_pages": {"type": "integer", "example": 4},
                "next":        {"type": "string",  "nullable": True, "format": "uri"},
                "previous":    {"type": "string",  "nullable": True, "format": "uri"},
                "results":     schema,
            },
        }


class LargePagination(PageNumberPagination):
    page_size            = 50
    page_size_query_param = "page_size"
    max_page_size        = 500
