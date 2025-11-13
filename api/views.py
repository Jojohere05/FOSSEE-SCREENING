from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.http import FileResponse
from django.contrib.auth.models import User
import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from .models import EquipmentDataset, Equipment
from .serializers import DatasetSummarySerializer, DatasetDetailSerializer, EquipmentSerializer

class CustomAuthToken(ObtainAuthToken):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username
        })

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = EquipmentDataset.objects.all()
    serializer_class = DatasetSummarySerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DatasetDetailSerializer
        return DatasetSummarySerializer
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """Upload CSV file and process it"""
        file = request.FILES.get('file')
        
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file.name.endswith('.csv'):
            return Response({'error': 'Only CSV files are allowed'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Read CSV with pandas
            df = pd.read_csv(file)
            
            # Validate required columns
            required_cols = ['Equipment Name', 'Type', 'Flowrate', 'Pressure', 'Temperature']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                return Response({
                    'error': f'Missing required columns: {", ".join(missing_cols)}',
                    'required_columns': required_cols,
                    'found_columns': list(df.columns)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate statistics
            total_count = len(df)
            avg_flowrate = float(df['Flowrate'].mean())
            avg_pressure = float(df['Pressure'].mean())
            avg_temperature = float(df['Temperature'].mean())
            
            # Save file pointer to beginning for storage
            file.seek(0)
            
            # Create dataset record
            dataset = EquipmentDataset.objects.create(
                name=file.name,
                uploaded_by=request.user,
                file=file,
                total_count=total_count,
                avg_flowrate=avg_flowrate,
                avg_pressure=avg_pressure,
                avg_temperature=avg_temperature
            )
            
            # Store individual equipment data
            equipment_objects = []
            for _, row in df.iterrows():
                equipment_objects.append(Equipment(
                    dataset=dataset,
                    name=row['Equipment Name'],
                    type=row['Type'],
                    flowrate=float(row['Flowrate']),
                    pressure=float(row['Pressure']),
                    temperature=float(row['Temperature'])
                ))
            
            Equipment.objects.bulk_create(equipment_objects)
            
            # Keep only last 5 datasets
            old_datasets = EquipmentDataset.objects.all()[5:]
            for old_dataset in old_datasets:
                old_dataset.file.delete()  # Delete file from storage
                old_dataset.delete()
            
            serializer = DatasetDetailSerializer(dataset)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except pd.errors.EmptyDataError:
            return Response({'error': 'CSV file is empty'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Error processing CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get detailed summary with type distribution"""
        dataset = self.get_object()
        equipments = dataset.equipments.all()
        
        # Calculate type distribution
        type_distribution = {}
        for equipment in equipments:
            eq_type = equipment.type
            type_distribution[eq_type] = type_distribution.get(eq_type, 0) + 1
        
        # Get all equipment data
        equipment_data = EquipmentSerializer(equipments, many=True).data
        
        return Response({
            'id': dataset.id,
            'name': dataset.name,
            'uploaded_at': dataset.uploaded_at,
            'total_count': dataset.total_count,
            'averages': {
                'flowrate': round(dataset.avg_flowrate, 2),
                'pressure': round(dataset.avg_pressure, 2),
                'temperature': round(dataset.avg_temperature, 2)
            },
            'type_distribution': type_distribution,
            'equipments': equipment_data
        })
    
    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get last 5 uploaded datasets"""
        datasets = EquipmentDataset.objects.all()[:5]
        serializer = DatasetSummarySerializer(datasets, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def generate_pdf(self, request, pk=None):
        """Generate PDF report for a dataset"""
        dataset = self.get_object()
        equipments = dataset.equipments.all()
        
        # Create PDF in memory
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Title
        p.setFont("Helvetica-Bold", 20)
        p.drawString(1*inch, height - 1*inch, "Equipment Analysis Report")
        
        # Dataset info
        p.setFont("Helvetica", 12)
        y = height - 1.5*inch
        p.drawString(1*inch, y, f"Dataset: {dataset.name}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Uploaded: {dataset.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')}")
        y -= 0.3*inch
        p.drawString(1*inch, y, f"Uploaded by: {dataset.uploaded_by.username}")
        
        # Summary Statistics
        y -= 0.5*inch
        p.setFont("Helvetica-Bold", 14)
        p.drawString(1*inch, y, "Summary Statistics")
        
        y -= 0.3*inch
        p.setFont("Helvetica", 11)
        p.drawString(1*inch, y, f"Total Equipment Count: {dataset.total_count}")
        y -= 0.25*inch
        p.drawString(1*inch, y, f"Average Flowrate: {dataset.avg_flowrate:.2f}")
        y -= 0.25*inch
        p.drawString(1*inch, y, f"Average Pressure: {dataset.avg_pressure:.2f}")
        y -= 0.25*inch
        p.drawString(1*inch, y, f"Average Temperature: {dataset.avg_temperature:.2f}")
        
        # Type Distribution
        y -= 0.5*inch
        p.setFont("Helvetica-Bold", 14)
        p.drawString(1*inch, y, "Equipment Type Distribution")
        
        type_dist = {}
        for eq in equipments:
            type_dist[eq.type] = type_dist.get(eq.type, 0) + 1
        
        y -= 0.3*inch
        p.setFont("Helvetica", 11)
        for eq_type, count in sorted(type_dist.items()):
            p.drawString(1.2*inch, y, f"{eq_type}: {count}")
            y -= 0.25*inch
        
        # Equipment Details Table Header
        y -= 0.3*inch
        if y < 2*inch:  # Start new page if needed
            p.showPage()
            y = height - 1*inch
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(1*inch, y, "Equipment Details")
        
        y -= 0.3*inch
        p.setFont("Helvetica-Bold", 9)
        p.drawString(1*inch, y, "Name")
        p.drawString(3*inch, y, "Type")
        p.drawString(4.5*inch, y, "Flowrate")
        p.drawString(5.5*inch, y, "Pressure")
        p.drawString(6.5*inch, y, "Temp")
        
        # Equipment Details
        y -= 0.05*inch
        p.line(1*inch, y, 7.5*inch, y)
        y -= 0.2*inch
        
        p.setFont("Helvetica", 8)
        for eq in equipments:
            if y < 1*inch:  # New page if needed
                p.showPage()
                y = height - 1*inch
                p.setFont("Helvetica", 8)
            
            p.drawString(1*inch, y, eq.name[:20])
            p.drawString(3*inch, y, eq.type)
            p.drawString(4.5*inch, y, f"{eq.flowrate:.1f}")
            p.drawString(5.5*inch, y, f"{eq.pressure:.1f}")
            p.drawString(6.5*inch, y, f"{eq.temperature:.1f}")
            y -= 0.2*inch
        
        # Footer
        p.setFont("Helvetica-Oblique", 8)
        p.drawString(1*inch, 0.5*inch, "Generated by Chemical Equipment Visualizer")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'equipment_report_{dataset.id}.pdf')