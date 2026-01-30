from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
import uuid


class CustomPagination(LimitOffsetPagination):
    default_limit = 100
    max_limit = 500
    
    def get_paginated_response(self, data):
        next_offset = self.offset + self.limit
        has_next = next_offset < self.count
        
        return Response({
            "meta": {
                "query_time": 0.5, #Mock olduğu için sabit verdim
                "pagination": {
                    "offset": self.offset,
                    "limit": self.limit,
                    "total": self.count,
                    "next": str(next_offset) if has_next else ""  
                },
                "trace_id": str(uuid.uuid4())
            },
            "errors": None,
            "resources": data  
        })
