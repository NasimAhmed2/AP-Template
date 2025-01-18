from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home, name='home'),
    path('upload-invoice/', views.upload_invoice, name='upload_invoice'),
    path('upload-opengrn/', views.upload_opengrn, name='upload_opengrn'),
    path('invoice-display/', views.invoice_display, name='invoice_display'),
    path('show-opengrn/', views.show_grn, name='show_grn'),
    path('show-invoice/', views.show_invoices, name='show_invoices'),
    path('save-template/', views.save_template, name='save_template'),
    path('export-templates/', views.export_templates, name='export_templates'),
    path('update-status/', views.update_status, name='update_status'),
    path('invoicepdf-show/', views.pdf_show, name='pdf_show'),
    path('show-templates/', views.show_templates, name='show_templates'),
    path('reset_project/', views.reset_project, name='reset_project'),
]

if settings.DEBUG:  # Only for development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
