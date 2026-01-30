from rest_framework import serializers
from .models import HostGroup, Device, DeviceState


class HostGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostGroup
        fields = '__all__'


class DeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['device_id']


class DeviceDetailSerializer(serializers.ModelSerializer):

    groups = serializers.PrimaryKeyRelatedField(
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = Device
        fields = '__all__'


class DeviceStateSerializer(serializers.ModelSerializer):

    id = serializers.CharField(source='device.device_id')
    
    class Meta:
        model = DeviceState
        fields = ['id', 'state']
