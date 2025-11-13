from django.db import models
from django.contrib.auth.models import User

class EquipmentDataset(models.Model):
    name = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='datasets/')
    
    # Summary statistics
    total_count = models.IntegerField()
    avg_flowrate = models.FloatField()
    avg_pressure = models.FloatField()
    avg_temperature = models.FloatField()
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.name} ({self.uploaded_at.strftime('%Y-%m-%d %H:%M')})"

class Equipment(models.Model):
    dataset = models.ForeignKey(EquipmentDataset, on_delete=models.CASCADE, related_name='equipments')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    flowrate = models.FloatField()
    pressure = models.FloatField()
    temperature = models.FloatField()
    
    def __str__(self):
        return f"{self.name} - {self.type}"