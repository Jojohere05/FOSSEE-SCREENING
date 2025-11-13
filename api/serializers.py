from rest_framework import serializers
from .models import EquipmentDataset, Equipment

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['id', 'name', 'type', 'flowrate', 'pressure', 'temperature']

class DatasetSummarySerializer(serializers.ModelSerializer):
    equipment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = EquipmentDataset
        fields = ['id', 'name', 'uploaded_at', 'total_count', 'avg_flowrate', 
                  'avg_pressure', 'avg_temperature', 'equipment_count']
    
    def get_equipment_count(self, obj):
        return obj.equipments.count()

class DatasetDetailSerializer(serializers.ModelSerializer):
    equipments = EquipmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = EquipmentDataset
        fields = ['id', 'name', 'uploaded_at', 'total_count', 'avg_flowrate',
                  'avg_pressure', 'avg_temperature', 'equipments']