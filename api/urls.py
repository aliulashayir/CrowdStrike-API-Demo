from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health),
    path('devices/host-groups/', views.host_groups),
    path('devices/devices/', views.device_list),
    path('devices/entities/', views.device_entities),
    path('devices/entities/online-state/', views.online_state),
]
