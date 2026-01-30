from django.db import models


class HostGroup(models.Model):
    
    id = models.CharField(max_length=32, primary_key=True)
    group_type = models.CharField(max_length=50) 
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assignment_rule = models.CharField(max_length=200, blank=True)
    created_by = models.CharField(max_length=200)
    created_timestamp = models.DateTimeField()
    modified_by = models.CharField(max_length=200)
    modified_timestamp = models.DateTimeField()

    class Meta:
        ordering = ['name'] 

    def __str__(self):
        return self.name


class Device(models.Model):
    
    device_id = models.CharField(max_length=32, primary_key=True)
    cid = models.CharField(max_length=32)
    hostname = models.CharField(max_length=200)
    external_ip = models.GenericIPAddressField(null=True, blank=True)
    local_ip = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=20)
    platform_name = models.CharField(max_length=50)
    os_version = models.CharField(max_length=50)
    agent_version = models.CharField(max_length=50)
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    status = models.CharField(max_length=20)
    system_manufacturer = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=50)
    
    
    groups = models.ManyToManyField(HostGroup, related_name='devices')

    def __str__(self):
        return self.hostname


class DeviceState(models.Model):
    
    device = models.OneToOneField(
        Device, 
        on_delete=models.CASCADE, 
        primary_key=True,
        related_name='online_state'
    )
    state = models.CharField(max_length=20)  # online, offline, unknown

    def __str__(self):
        return f"{self.device.hostname}: {self.state}"
