from django.db import models
from django.contrib.auth.models import User  # Built-in User model

class InvoiceDetail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invoices")  # Link to User model
    file_name = models.CharField(max_length=255, unique=True)  # Unique constraint
    path = models.TextField()
    upload_date = models.TextField(blank=True, null=True)
    okay_status = models.TextField(blank=True, null=True)
    okay_message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='waiting')

    def __str__(self):
        return f"{self.file_name} - {self.status}"
