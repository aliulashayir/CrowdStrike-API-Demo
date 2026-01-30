from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.response import Response
from rest_framework import status
from .paginators import CustomPagination
from .models import HostGroup, Device, DeviceState
from .serializers import HostGroupSerializer, DeviceListSerializer, DeviceDetailSerializer, DeviceStateSerializer   
import uuid


@api_view(["GET"])
@permission_classes([AllowAny]) 
def health(request):
    return Response({"message: Alive"},status = status.HTTP_200_OK)

@api_view(["GET"])
@authentication_classes([OAuth2Authentication])
@permission_classes([]) 
def host_groups(request):
    limit = request.query_params.get("limit")
    offset = request.query_params.get("offset")
    
    paginator = CustomPagination()

    hosts = HostGroup.objects.all()
    result = paginator.paginate_queryset(hosts, request)
    serializer = HostGroupSerializer(result, many = True)

    return paginator.get_paginated_response(serializer.data)

    
@api_view(["GET"])
@authentication_classes([OAuth2Authentication])
@permission_classes([]) 
def device_list(request):
    limit = request.query_params.get("limit")
    offset = request.query_params.get("offset")

    paginator = CustomPagination()
    devices = Device.objects.all()
    result = paginator.paginate_queryset(devices, request)
    serializer = DeviceListSerializer(result, many = True)

    return paginator.get_paginated_response(serializer.data)

@api_view(["POST"])
@authentication_classes([OAuth2Authentication])
@permission_classes([]) 
def device_entities(request):
    ids = request.data.get('ids', [])
    
    devices = Device.objects.filter(device_id__in=ids)
    found_ids = set(devices.values_list('device_id', flat=True))
    missing_ids = set(ids) - found_ids
    
    errors = None
    if missing_ids:
        errors = []
        for id in missing_ids:
            errors.append({"id": id, "message": "Device not found"}) 
   
    serializer = DeviceDetailSerializer(devices, many=True)
    
    return Response({
        "meta": {
            "query_time": 0.5,
            "trace_id": str(uuid.uuid4())
        },
        "resources": serializer.data,
        "errors": errors
    })



@api_view(["POST"])
@authentication_classes([OAuth2Authentication])
@permission_classes([]) 
def online_state(request):
    ids = request.data.get("ids",[])
    
    devices = DeviceState.objects.all().filter(device_id__in = ids)
    found_ids = set(devices.values_list('device_id', flat=True))
    missing_ids = set(ids) - found_ids
    
    errors = None
    if missing_ids:
        errors = []
        for id in missing_ids:
            errors.append({"id": id, "message": "Device not found"}) 
   
    serializer = DeviceStateSerializer(devices, many=True)
    
    return Response({
        "meta": {
            "query_time": 0.5,
            "trace_id": str(uuid.uuid4())
        },
        "resources": serializer.data,
        "errors": errors
    })