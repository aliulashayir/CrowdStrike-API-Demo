import time
from django.http import JsonResponse


class RateLimitMiddleware:
    
    remaining = 100 
    reset_time = time.time() + 60  
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        test_mode = request.GET.get('test_mode')
        
        # 1. Rate limit hit simülasyonu
        if test_mode == 'rate_limit_hit':
            RateLimitMiddleware.remaining = 0
            RateLimitMiddleware.reset_time = time.time() + 5  
            response = JsonResponse({
                "meta": {"error": "Rate limit exceeded"},
                "errors": ["Too many requests"]
            }, status=429)
            response["X-RateLimit-Remaining"] = "0"
            response["X-RateLimit-RetryAfter"] = str(int(RateLimitMiddleware.reset_time))
            return response
        
        # 2. Server error simülasyonu
        if test_mode == 'server_error':
            response = JsonResponse({
                "meta": {"error": "Internal server error"},
                "errors": ["Server temporarily unavailable"]
            }, status=500)
            response["X-RateLimit-Remaining"] = str(self.remaining)
            response["X-RateLimit-RetryAfter"] = str(int(self.reset_time))
            return response
        
        # 3. Slow response simülasyonu
        if test_mode == 'slow_response':
            time.sleep(5)
        

        self._check_reset()
        

        response = self.get_response(request)
        

        response["X-RateLimit-Remaining"] = str(self.remaining)
        response["X-RateLimit-RetryAfter"] = str(int(self.reset_time))
        

        RateLimitMiddleware.remaining = max(0, self.remaining - 1)
        
        return response
    
    def _check_reset(self):
        if time.time() > RateLimitMiddleware.reset_time:
            RateLimitMiddleware.remaining = 100
            RateLimitMiddleware.reset_time = time.time() + 60
