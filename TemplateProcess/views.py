from django.shortcuts import render
from django.http import HttpResponse, Http404
import pandas as pd
from django.core.files.storage import FileSystemStorage
import os
from django.http import FileResponse, JsonResponse
from zipfile import ZipFile
import io
import time
from datetime import date
from django.contrib import messages
from django.shortcuts import redirect
import requests
import json
import shutil
import datetime
from django.conf import settings
from django.core.files.storage import default_storage
from .diffrent_functions import filingstatus,Table_data,InvoiceTable_vs_GrnTable,all_okay,Invoicetable_vs_Grntable_compare
from .Template_formation import template_formation, retain_two_rows
# from .sqlite_function import ensure_table_and_update
import sqlite3
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import InvoiceDetail


# Create your views here.
@login_required
def home(request):
    return render(request, 'home.html')





def register(request):
    if request.method == "POST":
        password = request.POST["password"]
        email = request.POST["email"]
        confirm_password = request.POST["confirm_password"]

        if User.objects.filter(username=email).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")
        
        if password == confirm_password:
            user = User.objects.create_user(username=email, email=email, password=password)
            messages.success(request, "Registration successful. Please log in.")
            return redirect("login")
        else:
            messages.success(request, "Confirm password did not match. Please Try Again.")
            return redirect("login")

    return render(request, "register.html")

def user_login(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Store the user's ID in the session
            request.session["user_id"] = user.id  # or user.pk
            next_url = request.GET.get('next', 'home')  # Redirect to 'next' or home page
            return redirect(next_url)
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("login")

    return render(request, "login.html")

def user_logout(request):
    logout(request)
    request.session.flush()  # Clears all session data
    return redirect("login")

def save_invoice_detail(user, file_name, upload_date, path, okay_status=None, okay_message=None, status='waiting'):
    """
    Saves or updates the invoice details for a user.

    Args:
        user (User): The user associated with the invoice.
        file_name (str): The name of the file.
        path (str): The full path of the file.
        okay_status (str, optional): The status of the invoice. Defaults to None.
        okay_message (str, optional): The message related to the invoice. Defaults to None.
        status (str, optional): The status of the invoice. Defaults to 'waiting'.
    """
    try:
        # Create or update the invoice detail
        invoice, created = InvoiceDetail.objects.update_or_create(
            user=user,
            file_name=file_name,
            defaults={
                'upload_date':upload_date,
                'path': path,
                'okay_status': okay_status,
                'okay_message': okay_message,
                'status': status,
            }
        )
        if created:
            print(f"Invoice '{file_name}' created for user {user.username}.")
        else:
            print(f"Invoice '{file_name}' updated for user {user.username}.")
    except Exception as e:
        print(f"Error saving invoice '{file_name}': {e}")


@login_required
def pdf_show(request):
    user = request.user  # Get the logged-in user
    user_index = user.id
    # Get the PDF file name from the URL parameter
    response_file = request.GET.get('response_file')
    pdf_path = os.path.join(settings.MEDIA_ROOT, "invoices", str(user.id), response_file)
    # # Define the folder where your PDF files are stored
    # response_dir = os.path.join(settings.MEDIA_ROOT, "invoices")
    # pdf_path = os.path.join(response_dir, response_file)

    # Check if the file exists
    if not os.path.exists(pdf_path):
        raise Http404("PDF file not found.")

    # Pass the URL-relative path to the template
    pdf_url = f"{settings.MEDIA_URL}invoices/{user_index}/{response_file}"
    print(pdf_url)

    return render(request, 'invoice_pdf_show.html', {'pdf_name': pdf_url})
@login_required
def export_templates(request):
    if request.method == "POST":
        try:
            # Paths to the two Excel files
            user_index = request.session.get("user_id")
            base_dir = os.path.join(settings.BASE_DIR, 'TemplateData', str(user_index))
            # Define user-specific file paths
            file2_path = os.path.join(base_dir, 'Templates.xlsx')
            file1_path = os.path.join(base_dir, 'header.xlsx')
            # Check if files exist
            if not os.path.exists(file1_path) or not os.path.exists(file2_path):
                return JsonResponse({"message": "One or more files not found."}, status=404)

            # Create an in-memory ZIP file
            zip_buffer = io.BytesIO()
            with ZipFile(zip_buffer, 'w') as zip_file:
                zip_file.write(file1_path, arcname='header.xlsx')  # Add the first file
                zip_file.write(file2_path, arcname='templates.xlsx')  # Add the second file

            # Reset buffer position to the beginning
            zip_buffer.seek(0)

            # Serve the ZIP file as a response
            response = FileResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="templates.zip"'
            path = [file2_path,file1_path]
            retain_two_rows(path)
            return response
            
        except Exception as e:
            return JsonResponse({"message": f"Error: {str(e)}"}, status=500)
    return JsonResponse({"message": "Invalid request method"}, status=400)

@login_required
def show_templates(request, message=[]):
    try:
        user_index = request.session.get("user_id")
        user = request.user
        # Read the first Excel sheet
        file_path_1 = os.path.join(settings.BASE_DIR, 'TemplateData', str(user_index), 'header.xlsx')
        # file_path_1 = 'TemplateData/header.xlsx'
        sheet_1 = pd.read_excel(file_path_1)

        # Read the second Excel sheet
        file_path_2 = os.path.join(settings.BASE_DIR, 'TemplateData', str(user_index), 'Templates.xlsx')
        # file_path_2 = 'TemplateData/Templates.xlsx'
        sheet_2 = pd.read_excel(file_path_2)

        # Convert the dataframes to HTML tables
        sheet_1_html = sheet_1.to_html(index=False)
        sheet_2_html = sheet_2.to_html(index=False)

        # Render the 'save_template.html' template
        return render(request, 'save_template.html', {
            'message': message,
            'sheet_1_html': sheet_1_html,
            'sheet_2_html': sheet_2_html
        })
    except Exception as e:
        # Handle exceptions
        message =[f"Error: {str(e)}"]
        return render(request, 'save_template.html', {
            'message': message,
            'sheet_1_html': '',
            'sheet_2_html': ''
        })
@login_required
def save_template(request):
    # Check if the Save Template button was clicked
    if request.method == "POST":
        user_index = request.session.get("user_id")
        user = request.user
        try:
            # Get the list of selected files from the POST data
            selected_files = request.POST.get('selected_files', '[]')
            selected_files = json.loads(selected_files)  # Convert JSON string to Python list

            # Perform your desired actions with the selected files
            print("Selected files:", selected_files)

            # Generate the message by processing the selected files
            message = template_formation(selected_files,user_index,user)
            
            if isinstance(message, str):
                # Wrap the string in a list
                message = [message]

            # Redirect to show_templates with the generated message
            return show_templates(request, message)

        except Exception as e:
            # Handle exceptions
            message = [f"Error: {str(e)}"]
            return show_templates(request, message)


    
@login_required
def show_grn(request):
    context = {"data": None, "columns": None, "message": ""}
    user_index = request.session.get("user_id")
    # Absolute path to GRN_Data directory
    path = os.path.join(settings.BASE_DIR, 'GRN_Data', str(user_index), 'Open_GRN_Data.csv')
    try:
        data = pd.read_csv(path)
        context["data"] = data.values.tolist()
        context["columns"] = data.columns.tolist()

    except:
        context['message'] = 'Please Upload Open GRN reports , found not reports to display'
    return render(request, 'show_opengrn.html', context)
@login_required
def invoice_display(request):
    context = {}
    # Get data from session
    # api_response = request.session.get('api_response', {})
    # result = api_response.get('result', {})
    # Define the directory where responses are saved
    user = request.user  # Get the logged-in user
    user_index = request.session.get("user_id")
    
    # response_dir = os.path.join(settings.MEDIA_ROOT, "responses", user_index)
    response_dir = os.path.join(settings.MEDIA_ROOT, "responses", str(user.id))
    
    # Get the response file name from the query parameter
    response_file_name = request.GET.get('response_file')
    # print(response_file_name)
    if response_file_name:
        # Construct the full path to the response file
        response_file = os.path.join(response_dir, response_file_name)
        # print(response_file)
        try:
            # Check if the response file exists
            if os.path.exists(response_file):
                # Load the response data from the file
                with open(response_file, "r") as file:
                    api_response = json.load(file)
                    # print(api_response)
                
                # Extract relevant data
                result = api_response.get("result", {})
                # Extract default data
                invoice_data = result.get('Invoice_data', {})
                # print(invoice_data)
                table_data_json = result.get('CHECKS', {}).get('table_data', {}).get('Table_Check_data', '[]')
                table_data = json.loads(table_data_json) if isinstance(table_data_json, str) else table_data_json
                # print(table_data)
                ##tax check table disintegration into 5 tables
                account_check = result.get('CHECKS', {}).get('Account_check', {})
                tax_check = result.get('CHECKS', {}).get('tax_check', {})
                Filinq_status_data = result.get('CHECKS', {}).get('data_from_gst', {}).get('Filing Status', [])
                YES_NO = {'Okay':'YES',
                        'Not Okay': 'NO'}
                YES_NO_ = {'Okay':'NO',
                        'Not Okay': 'YES',
                        'YES':'NO',
                        "NO":"YES"}
                Okay_NOtOkay_ = {'NO':'Okay',
                        'YES':'Not Okay',
                        }
                try:
                    tax_check_companygst_mentioned = {}
                    tax_check_vendorgst_mentioned = {}
                    tax_check_vendorfilingstatus = {}
                    # print(Filinq_status_data)
                    # print('hello--1')
                    # filingstatus_rslt = filingstatus(Filinq_status_data)
                    # print(filingstatus_rslt)
                    tax_check_taxpayertype_filingfrequncy = {}
                    tax_check_correctgstcharged = {}
                    tax_check_RCM_Blockedcredit = {} 
                    tax_check_data = {}

                    tax_check_companygst_mentioned['Is GST No. of the company mentioned on the invoice (When company registered in GST)?'] = tax_check['Company_Gst_mentioned']['status']
                    tax_check_companygst_mentioned['Company GST Number -As per Invoice'] = invoice_data.get('Cutomer Gst No.')
                    tax_check_companygst_mentioned['Company GST Number-As per Masters in WFS'] = ' '
                    tax_check_companygst_mentioned['Is Company GST No. as per invoice & as per Masters matching?'] = ' '

                    gstcharge_stats = account_check['gstnumber_gstcharged']['status']
                    tax_check_vendorgst_mentioned['Is Vendor GST No. mentioned on the invoice (when GST Charged)?'] = tax_check['Vendor_Gst_mentioned']['status']
                    tax_check_vendorgst_mentioned['Vendor GST Number -As per Invoice'] = invoice_data.get('Vendor Gst No.')
                    tax_check_vendorgst_mentioned['Is GST No. of vendor mentioned on the invoice valid as per GST Portal?'] = tax_check['Vendor_Gst_Valid']['status']
                    tax_check_vendorgst_mentioned['Is Vendor GST Status Active on GST Portal?'] = tax_check['Vendor_Gst_Active']['status']
                    tax_check_vendorgst_mentioned['Is GST Charged on invoice (when GST No. of vendor mentioned)?'] = YES_NO.get(gstcharge_stats) 

                    # tax_check_vendorfilingstatus['Is Vendor regular in filing GST(3B) Return?'] = filingstatus_rslt['status']
                    # tax_check_vendorfilingstatus['Filing Status of Previous month'] = filingstatus_rslt['month']
                    # tax_check_vendorfilingstatus['Filing Status - Earlier to Previous month1'] = filingstatus_rslt['month1']
                    # tax_check_vendorfilingstatus['Filing Status - Earlier to Previous month2'] = filingstatus_rslt['month2']

                    tax_check_taxpayertype_filingfrequncy['Vendor Tax Payer Type as per GST Portal'] = tax_check['Vendor_TaxPayer_type']['status']
                    tax_check_taxpayertype_filingfrequncy['Vendor Filing Frequency as per GST Portal'] = tax_check['Vendor_Taxfiliging_Frequency']['status']

                    taxtypestatus = tax_check['tax_type_on_invoice']['status']
                    tax_check_correctgstcharged['Is correct tax type is charged on invoice (CGST&SGST/IGST)?'] = YES_NO.get(taxtypestatus)
                    tax_check_correctgstcharged['Company GST No. (First 2 Digits) (As per invoice)'] = invoice_data.get('Cutomer Gst No.')
                    tax_check_correctgstcharged['Vendor GST No. (First 2 Digits) (As per invoice)'] = invoice_data.get('Vendor Gst No.')

                    rcm_status = account_check['Invoice_RCM-Services']['status']
                    blockedcredit_status = account_check['Invoice_Blocked_Credit']['status']
                    tax_check_RCM_Blockedcredit['Is Invoice covered under RCM'] = YES_NO_.get(rcm_status)
                    tax_check_RCM_Blockedcredit['Reason of coverage under RCM'] = account_check['Invoice_RCM-Services']['Invoice_data']
                    tax_check_RCM_Blockedcredit['Is Invoice covered under Blocked Credit'] = YES_NO_.get(blockedcredit_status)
                    tax_check_RCM_Blockedcredit['Reason of coverage under Blocked credit'] = account_check['Invoice_Blocked_Credit']['Invoice_data']
                    
                    tax_check_data['tax_check_companygst_mentioned'] = tax_check_companygst_mentioned
                    tax_check_data['tax_check_vendorgst_mentioned'] = tax_check_vendorgst_mentioned
                    tax_check_data['tax_check_vendorfilingstatus'] = tax_check_vendorfilingstatus
                    tax_check_data['tax_check_taxpayertype_filingfrequncy'] = tax_check_taxpayertype_filingfrequncy
                    tax_check_data['tax_check_correctgstcharged'] = tax_check_correctgstcharged
                    tax_check_data['tax_check_RCM_Blockedcredit'] = tax_check_RCM_Blockedcredit
                except:
                    pass
                ## account check table disintegration into smaller table
                Checks = {}
                try:
                    try:
                        invoice_vs_gstin_protal = {}
                        company_name = {}
                        company_address = {}

                        company_name['parameter'] = 'Company Name'
                        company_name['As_per_Invoice'] = account_check['Customer_Name']['Invoice_data']
                        company_name['As_per_GST_Portal'] = account_check['Customer_Name']['Gst_Portal']
                        company_name['As_per_GST_Portal_legal'] = result.get('CHECKS', {}).get('data_from_gst', {}).get('customer_gst_data', {}).get('lgnm', None)
                        company_name['Result'] = account_check['Customer_Name']['status']
                        # print('this--1')
                        company_address['parameter'] = 'Company Address'
                        company_address['As_per_Invoice'] = account_check['Customer_Adress']['Invoice_data']
                        company_address['As_per_GST_Portal'] = account_check['Customer_Adress']['Gst_Portal']
                        company_address['Result'] = account_check['Customer_Adress']['status']
                        # print('this--2')
                        invoice_vs_gstin_protal['company_name'] = company_name
                        invoice_vs_gstin_protal['company_address'] = company_address
                        # print('this--3')
                        Checks['invoice_vs_gstin_protal'] = invoice_vs_gstin_protal
                    except Exception as e:
                        print(f"Error--1 : {str(e)}")

                    try:
                        invoice_validations = {}
                        invoice_complete = {}
                        invoice_valid = {}
                        invoice_Date = {}
                        invoice_No = {}
                        invoice_pre_year = {}
                        Comapny_gst_no_mentioned = {}
                        Gst_charged = {}
                        Vendor_gst_no_mentioned = {}
                        gst_type = {}
                        rcm_covered = {}
                        blocked_credit = {}
                        try:
                            invoice_complete['parameter'] = 'Invoice Complete?'
                            invoice_complete['Result'] = account_check['Complete_Invoice']['status']
                            invoice_complete['As_per_Invoice'] = 'Supplier Name, PAN, Customer Name, Customer Address, GST/PAN, Bill No., Bill Date, Basic Value, Total Value'
                            invoice_validations['invoice_complete'] = invoice_complete
                        except Exception as e:
                            print(f"Error--2 : {str(e)}")
                        try:
                            invoice_valid['parameter'] = 'Invoice Valid ?'
                            invoice_valid['Result'] = account_check['valid_invoice']['status']
                            invoice_valid['As_per_Invoice'] = 'Should not mention - PI/Estimate/Commercial Invoice/Supply invoice/Challan'
                            invoice_validations['invoice_valid'] = invoice_valid
                        except Exception as e:
                            print(f"Error--3 : {str(e)}")
                        try:
                            okay1 = account_check['Invoice_Date']['status']
                            date_ = account_check['Invoice_Date']['Invoice_data']
                            invoice_Date['parameter'] = 'Invoice Date'
                            invoice_Date['Result'] = YES_NO.get(okay1)
                            invoice_Date['As_per_Invoice'] = f'Invoice Date: {date_}'
                            invoice_validations['invoice_Date'] = invoice_Date
                        except Exception as e:
                            print(f"Error---4 : {str(e)}")
                        try:
                            invoice_ = account_check['Invoice_Number']['Invoice_data']
                            okay2 = account_check['Invoice_Number']['status']
                            invoice_No['parameter'] = 'Invoice No.'
                            invoice_No['Result'] = YES_NO.get(okay2)
                            invoice_No['As_per_Invoice'] = f'Invoice No.: {invoice_}'
                            invoice_validations['invoice_No'] = invoice_No
                        except Exception as e:
                            print(f"Error---5 : {str(e)}")
                        try:
                            date_ = account_check['Invoice_Date']['Invoice_data']
                            pre_yr_stst = account_check['Pre_year']['status']
                            # print(pre_yr_stst)
                            invoice_pre_year['parameter'] = 'Invoice of current Year'
                            invoice_pre_year['Result'] = YES_NO_.get(pre_yr_stst)
                            invoice_pre_year['As_per_Invoice'] = f'Invoice Date: {date_}'
                            invoice_validations['invoice_pre_year'] = invoice_pre_year
                        except Exception as e:
                            print(f"Error---6 : {str(e)}")
                        try:
                            Comapny_gst_no_mentioned['parameter'] = 'GST No. of Company Mentioned?'
                            Comapny_gst_no_mentioned['Result'] = tax_check['Company_Gst_mentioned']['status']
                            Comapny_gst_no_mentioned['As_per_Invoice'] = invoice_data.get('Cutomer Gst No.')
                            invoice_validations['Comapny_gst_no_mentioned'] = Comapny_gst_no_mentioned
                        except Exception as e:
                            print(f"Error---7 : {str(e)}")
                        try:
                            Gst_charged_stst = account_check['gstnumber_gstcharged']['status']
                            # print(Gst_charged_stst)
                            Gst_charged['parameter'] = 'GST Charged on invoice? (When vendor registered)'
                            Gst_charged['Result'] = YES_NO.get(Gst_charged_stst)
                            Gst_charged['As_per_Invoice'] = ''
                            invoice_validations['Gst_charged'] = Gst_charged
                        except Exception as e:
                            print(f"Error---8 : {str(e)}")
                        try:
                            Vendor_gst_no_mentioned['parameter'] = 'GST No. of Vendor Mentioned? (When GST Charged)'
                            Vendor_gst_no_mentioned['Result'] = tax_check['Vendor_Gst_mentioned']['status']
                            Vendor_gst_no_mentioned['As_per_Invoice'] = invoice_data.get('Vendor Gst No.')
                            invoice_validations['Vendor_gst_no_mentioned'] = Vendor_gst_no_mentioned
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            taxtypestatus = tax_check['tax_type_on_invoice']['status']
                            gst_type['parameter'] = 'GST Type -  Correctly Charged'
                            gst_type['Result'] = YES_NO.get(taxtypestatus)
                            gst_type['As_per_Invoice'] = ''
                            invoice_validations['gst_type'] = gst_type
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            rcm_status = account_check['Invoice_RCM-Services']['status']
                            # print(rcm_status)
                            rcm_covered['parameter'] = 'Invoice - Not Covered under RCM?'
                            rcm_covered['Result'] = YES_NO_.get(rcm_status)
                            rcm_covered['As_per_Invoice'] = account_check['Invoice_RCM-Services']['Invoice_data']
                            invoice_validations['rcm_covered'] = rcm_covered
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            blockedcredit_status = account_check['Invoice_Blocked_Credit']['status']
                            # print(blockedcredit_status)
                            blocked_credit['parameter'] = 'Invoice - Not Covered under Blocked Credit?'
                            blocked_credit['Result'] =YES_NO.get(blockedcredit_status)
                            blocked_credit['As_per_Invoice'] = account_check['Invoice_Blocked_Credit']['Invoice_data']
                            invoice_validations['blocked_credit'] = blocked_credit
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        Checks['invoice_validations'] = invoice_validations
                    except:
                        pass
                    try:
                        gst_portal_check = {}
                        vendor_gst_valid = {}
                        vendor_gst_active = {}
                        vendor_3B_filingstatus = {}
                        vendor_3B_filingstatus1 = {}
                        vendor_3B_filingstatus2 = {}
                        vendor_3B_filingstatus3 = {}
                        vendor_gstr1_filingstatus = {}
                        vendor_gstr1_filingstatus1 = {}
                        vendor_gstr1_filingstatus2 = {}
                        vendor_gstr1_filingstatus3 = {}
                        vendor_taxpayer_type = {}
                        vendor_filing_frquncy = {}
                        try:
                            vendor_gst_valid['parameter'] = 'GST No. of Vendor valid as per GSTN?'
                            vendor_gst_valid['Result'] = tax_check['Vendor_Gst_Valid']['status']
                            gst_portal_check['vendor_gst_valid'] = vendor_gst_valid
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            vendor_gst_active['parameter'] = 'GST No. of Vendor Active on GSTN?'
                            vendor_gst_active['Result'] = tax_check['Vendor_Gst_Active']['status']
                            gst_portal_check['vendor_gst_active'] = vendor_gst_active
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")

                        try:
                            tax_check['Vendor_Taxfiliging_Frequency']['status']
                            vendor_taxpayer_type['parameter'] = 'Vendor Tax Payer Type'
                            vendor_taxpayer_type['Result'] = tax_check['Vendor_TaxPayer_type']['status']
                            gst_portal_check['vendor_taxpayer_type'] = vendor_taxpayer_type
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            
                            vendor_filing_frquncy['parameter'] = 'Vendor Tax Payer - Filing Frequency'
                            vendor_filing_frquncy['Result'] = tax_check['Vendor_Taxfiliging_Frequency']['status']
                            gst_portal_check['vendor_filing_frquncy'] = vendor_filing_frquncy
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            filingstatus_rslt_3b , filingstatus_rslt_gstr1, df_gstr1, df_3b = filingstatus(Filinq_status_data)
                            df_gstr1_html= df_gstr1.to_html(index=False, classes="table table-bordered")
                            df_3b_html= df_3b.to_html(index=False, classes="table table-bordered")
                            ##gstr3b
                            vendor_3B_filingstatus['parameter'] = 'Vendor GSTR 3B Filing Status'
                            vendor_3B_filingstatus['Result'] = ''
                            gst_portal_check['vendor_3B_filingstatus'] = vendor_3B_filingstatus

                            vendor_3B_filingstatus1['parameter'] = 'Previous Month (Month 1)'
                            vendor_3B_filingstatus1['Result'] = filingstatus_rslt_3b['month']
                            gst_portal_check['vendor_3B_filingstatus1'] = vendor_3B_filingstatus1

                            vendor_3B_filingstatus2['parameter'] = 'Month prior to Month 1 (Month 2)'
                            vendor_3B_filingstatus2['Result'] = filingstatus_rslt_3b['month1']
                            gst_portal_check['vendor_3B_filingstatus2'] = vendor_3B_filingstatus2

                            vendor_3B_filingstatus3['parameter'] = 'Month prior to Month 2 (Month 3)'
                            vendor_3B_filingstatus3['Result'] = filingstatus_rslt_3b['month2']
                            gst_portal_check['vendor_3B_filingstatus3'] = vendor_3B_filingstatus3
                            ##gstr1
                            vendor_gstr1_filingstatus['parameter'] = 'Vendor GSTR 1 Filing Status'
                            vendor_gstr1_filingstatus['Result'] = ''
                            gst_portal_check['vendor_gstr1_filingstatus'] = vendor_gstr1_filingstatus

                            vendor_gstr1_filingstatus1['parameter'] = 'Previous Month (Month 1)'
                            vendor_gstr1_filingstatus1['Result'] = filingstatus_rslt_gstr1['month']
                            gst_portal_check['vendor_gstr1_filingstatus1'] = vendor_gstr1_filingstatus1

                            vendor_gstr1_filingstatus2['parameter'] = 'Month prior to Month 1 (Month 2)'
                            vendor_gstr1_filingstatus2['Result'] = filingstatus_rslt_gstr1['month1']
                            gst_portal_check['vendor_gstr1_filingstatus2'] = vendor_gstr1_filingstatus2

                            vendor_gstr1_filingstatus3['parameter'] = 'Month prior to Month 2 (Month 3)'
                            vendor_gstr1_filingstatus3['Result'] = filingstatus_rslt_gstr1['month2']
                            gst_portal_check['vendor_gstr1_filingstatus3'] = vendor_gstr1_filingstatus3
                        except Exception as e:
                            gst_portal_check = {}
                            print(f"Error while loading response: {str(e)}")
                        
                        Checks['gst_portal_check'] = gst_portal_check
                    except Exception as e:
                        print(f"Error while loading response: {str(e)}")
                    try:
                        income_tax_check = {}
                        vendor_pan_active = {}
                        vendor_pan_adhar_linked = {}
                        vendor_206AB = {}

                        try:
                            pan_stats = tax_check['Vendor_Pan_Active']['status']
                            vendor_pan_active['parameter'] = 'Vendor PAN Active'
                            vendor_pan_active['Result'] = YES_NO.get(pan_stats)
                            income_tax_check['vendor_pan_active'] = vendor_pan_active
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            pan_adhar_stats = tax_check['Vendor_Pan-Adhar_Linked']['status']
                            # print(pan_adhar_stats)
                            vendor_pan_adhar_linked['parameter'] = 'Vendor Aadhar & PAN linked (For Individual & Proprietor)'
                            vendor_pan_adhar_linked['Result'] = YES_NO.get(pan_adhar_stats)
                            income_tax_check['vendor_pan_adhar_linked'] = vendor_pan_adhar_linked
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        try:
                            vendor_206AB_stst = tax_check['Vendor_206AB']['status']
                            vendor_206AB['parameter'] = 'Vendor Defaulter u/s 206AB'
                            vendor_206AB['Result'] = YES_NO_.get(vendor_206AB_stst)
                            income_tax_check['vendor_206AB'] = vendor_206AB
                        except Exception as e:
                            print(f"Error while loading response: {str(e)}")
                        Checks['income_tax_check'] = income_tax_check
                    except Exception as e:
                        print(f"Error while loading response: {str(e)}")
                except:
                    pass

                

                try:
                    ##table data
                    Table_Data = {}
                    
                    tabledata_,check_2,check_3 = Table_data(table_data, invoice_data)
                    Table_Data['tabledata_'] = tabledata_
                    Table_Data['check_2'] = check_2
                    Table_Data['check_3'] = check_3
                    # print('this---2')
                    # print(Table_Data)
                except:
                    pass
                ##table_data vs grn data
                # print('this---3')
                grn_vs_inoice = {}
                try:
                    invoice_table,grn_data = InvoiceTable_vs_GrnTable(invoice_data,user_index)
                    # print('this---4')
                    # print(invoice_table,grn_data)
                    
                    if invoice_table[0] == 200:
                        grn_vs_inoice['invoice_data'] = invoice_table[1]
                        grn_vs_inoice['invoice_message'] = ''
                    else:
                        grn_vs_inoice['invoice_data'] = ''
                        grn_vs_inoice['invoice_message'] = invoice_table[1]
                    if grn_data[0] == 200:
                        grn_vs_inoice['grn_data'] = grn_data[1]
                        grn_vs_inoice['grn_message'] = ''
                    else:
                        grn_vs_inoice['grn_data'] = ''
                        grn_vs_inoice['grn_message'] = grn_data[1]
                except:
                    pass
                
                try:
                    invoice_table_vs_grn_data = Invoicetable_vs_Grntable_compare(invoice_data,user_index)
                    # print(invoice_table_vs_grn_data)
                except:
                    invoice_table_vs_grn_data = {}
                # print('this---5')
                # Pass data to context for rendering
                
                try:
                    # context = {
                    #     'active_tab': 'Invoice_data',
                    #     'invoice_data': invoice_data,
                    #     'Tax_check': tax_check_data,
                    #     'gst_data': result.get('CHECKS', {}).get('data_from_gst', {}),
                    #     'table_data' : Table_Data,
                    #     'Checks': Checks,
                    #     # 'Account_check':account_check_data,
                    #     'Filinq_frequency' : result.get('CHECKS', {}).get('data_from_gst', {}).get('Filing Frequency', []),
                    #     'Filinq_status' : Filinq_status_data,
                    #     'df_gstr1_html' : df_gstr1_html,
                    #     'df_3b_html': df_3b_html,
                    #     'grn_vs_invoice' : grn_vs_inoice,
                    #     'keys_with_tooltip': ['invoice_complete', 'invoice_valid'],
                    #     '2b_olive_color' : ['YES', 'Filed', 'Regular', 'Monthly', 'Okay'],
                    #     'Invoicetable_vs_Grntable_compare':invoice_table_vs_grn_data,
                        

                    #     # 'Filinq_status' : result.get('CHECKS', {}).get('data_from_gst', {}).get('Filing Status', [])
                    # }

                    context = {
                        'active_tab': 'Invoice_data',
                        'invoice_data': invoice_data if 'invoice_data' in locals() else {},
                        'Tax_check': tax_check_data if 'tax_check_data' in locals() else {},
                        'gst_data': result.get('CHECKS', {}).get('data_from_gst', {}),
                        'table_data': Table_Data if 'Table_Data' in locals() else {},
                        'Checks': Checks if 'Checks' in locals() else {},
                        'Filinq_frequency': result.get('CHECKS', {}).get('data_from_gst', {}).get('Filing Frequency', {}),
                        'Filinq_status': Filinq_status_data if 'Filinq_status_data' in locals() else {},
                        'df_gstr1_html': df_gstr1_html if 'df_gstr1_html' in locals() else '',
                        'df_3b_html': df_3b_html if 'df_3b_html' in locals() else '',
                        'grn_vs_invoice': grn_vs_inoice if 'grn_vs_inoice' in locals() else {},
                        'keys_with_tooltip': ['invoice_complete', 'invoice_valid'],
                        '2b_olive_color': ['YES', 'Filed', 'Regular', 'Monthly', 'Okay'],
                        'Invoicetable_vs_Grntable_compare': invoice_table_vs_grn_data if 'invoice_table_vs_grn_data' in locals() else {},
                    }

                    # print(context['Checks'])
                except Exception as e:
                    print(f"Error while loading response: {str(e)}")
                # print('this---6')
                # print(context)
            else:
                context["message"] = f"No response file found for: {response_file_name}"
        except Exception as e:
            context["message"] = f"Error while loading response: {str(e)}"
    else:
        context["message"] = "No response file specified."
    
    
    return render(request, 'invoice_display.html', context)


@login_required
def upload_invoice(request):
    context = {"message": ""}
    url = "https://ocrblueconsulting.azurewebsites.net/process-invoice-withchecks-updated"
    user_id = "BC_User1"
    password = "1234@India"
    
    user = request.user  # Get the logged-in user
    user_index = request.session.get("user_id")
    # print(user_index)
    # Define user-specific directories
    # Define user-specific directories
    invoice_dir = os.path.join(settings.MEDIA_ROOT, "invoices", str(user_index),)
    response_dir = os.path.join(settings.MEDIA_ROOT, "responses", str(user_index),)

    # Ensure the directories exist
    os.makedirs(invoice_dir, exist_ok=True)
    os.makedirs(response_dir, exist_ok=True)
    
    
    # print('hello--1')
    if request.method == 'POST' and request.FILES.getlist('files'):
        uploaded_files = request.FILES.getlist('files')
        responses = []
        # print(uploaded_files)
        for uploaded_file in uploaded_files:
            time.sleep(0.5)
            try:
                # print('hello--2')
                # Generate a unique name with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                
                unique_name = f"{timestamp}_{uploaded_file.name}"
                # print(current_date_)
                invoice_path = os.path.join(invoice_dir, unique_name)
                # print(invoice_path)
                with default_storage.open(invoice_path, 'wb+') as destination:
                    for chunk in uploaded_file.chunks():
                        destination.write(chunk)

                # Prepare the API request
                files = {'pdf_file': open(invoice_path, 'rb')}
                data = {'user_id': user_id, 'password': password, 'App': 'WFS'}

                # Make the API request
                response = requests.post(url, files=files, data=data)
                files['pdf_file'].close()  # Close file after request
                # print(response)
                if response.status_code == 200:
                    api_response = response.json()
                    # print(api_response)
                    all_okay_,api_response_ = all_okay(api_response)
                    # Save API response in a JSON file
                    okay_notokay = all_okay_['status']
                    okay_message = all_okay_['message']
                    # print(okay_message)
                    okay_message_ = ''
                    if not okay_message: 
                        pass
                    else:
                        for mess in okay_message:
                            # print(mess)
                            okay_message_ = okay_message_ + ' ' + mess

                    uploaded_file_name = os.path.join(response_dir, f"{timestamp}_{uploaded_file.name}.json")
                    response_file = os.path.join(response_dir, uploaded_file_name)
                    
                    with open(response_file, 'w') as f:
                        json.dump(api_response_, f, indent=4)
                    
                    # print("Calling the function to ensure table and update the database...")
                    # Save or update the database entry
                    save_invoice_detail(
                        user=user,
                        file_name=unique_name,
                        upload_date=timestamp,
                        path=invoice_path,
                        okay_status=okay_notokay,
                        okay_message=okay_message,
                        status='waiting'
                    )
                    print("Function call finished.")
                    responses.append(f"Processed {uploaded_file.name} successfully.")
                else:
                    print("Function call gave errror")
                    responses.append(f"Error for {uploaded_file.name}: {response.status_code} - {response.text}")
            
            except Exception as e:
                responses.append(f"Error for {uploaded_file.name}: {str(e)}")

        context['message'] = "\n".join(responses)
        return redirect('show_invoices')  # Redirect to the new page
    return render(request, 'upload_invoice.html', context)

    
@login_required
def update_status(request):
    if request.method == "POST":
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            invoice_name = data['invoice_name']
            status = data['status']
            name = data['name']
            reason = data['reason']

            # Construct the message
            okay_message = f"{status}, Updated by {name} for reason {reason}"

            try:
                # Get the invoice by file_name using Django's ORM
                invoice = InvoiceDetail.objects.get(user=request.user, file_name=invoice_name)

                # Update the fields
                invoice.okay_status = status
                invoice.okay_message = okay_message

                # Save the changes
                invoice.save()
                print('hello')
                
                response = {
                    "message": f"Status updated for {invoice_name}",
                    "success": True
                }
                return JsonResponse(response)

            except InvoiceDetail.DoesNotExist:
                # If the invoice does not exist
                response = {
                    "message": f"No invoice found with the name '{invoice_name}'",
                    "status": "error"
                }
                return JsonResponse(response)

            except Exception as e:
                # Handle other errors
                response = {
                    "message": f"Error updating status: {str(e)}",
                    "status": "error"
                }
                return JsonResponse(response)

        except Exception as e:
            # Handle JSON parsing errors or other issues
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    else:
        return JsonResponse({"success": False, "message": "Invalid request method."}, status=400)



import sqlite3
@login_required
def show_invoices(request):
    # Default filter is "waiting"
    status_filter = request.GET.get('status', 'waiting')
    user_index = request.session.get("user_id")
    # Query invoices based on the selected status
    if status_filter == 'all':
        # Fetch all invoices for the logged-in user
        invoices = InvoiceDetail.objects.filter(user=request.user)
    else:
        # Fetch invoices filtered by status for the logged-in user
        invoices = InvoiceDetail.objects.filter(user=request.user, status=status_filter)

    # Prepare context for rendering
    context = {
        'invoices': invoices,
        'selected_status': status_filter,
        'user_index':user_index,
    }
    return render(request, 'show_invoices.html', context)

@login_required
def reset_project(request):
    # Only proceed if the password is provided and matches
    if request.method == "POST":
        password = request.POST.get('password')

        # Check if the password is correct
        if password != '4321@4321':
            return HttpResponse('Incorrect password', status=403)

        # Define directories to delete
        invoice_dir = os.path.join(settings.MEDIA_ROOT, "invoices")
        response_dir = os.path.join(settings.MEDIA_ROOT, "responses")

        # Delete all files in the 'invoices' folder
        if os.path.exists(invoice_dir):
            for filename in os.listdir(invoice_dir):
                file_path = os.path.join(invoice_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)  # Permanently delete file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Permanently delete folder

        # Delete all files in the 'responses' folder
        if os.path.exists(response_dir):
            for filename in os.listdir(response_dir):
                file_path = os.path.join(response_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)  # Permanently delete file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Permanently delete folder

        # Connect to SQLite database
        db_path = os.path.join(settings.BASE_DIR, "db.sqlite3")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Delete all entries from the 'invoice_detail' table
        cursor.execute("DELETE FROM invoice_detail")
        conn.commit()

        # Close the database connection
        conn.close()

        # Show a success message
        messages.success(request, 'Project has been reset to initial state.')

        # Redirect to home page
        return redirect('home')

    # If GET request, show the password form
    return render(request, 'reset_project.html')

@login_required
def upload_opengrn(request):
    context = {"data": None, "columns": None, "message": ""}
    user_index = request.session.get("user_id")
    save_folder = os.path.join(settings.BASE_DIR, 'GRN_Data', str(user_index))

    # Ensure the save folder exists
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    if request.method == 'POST' and request.FILES.get('file'):
        # Handle file upload
        uploaded_file = request.FILES['file']
        # fs = FileSystemStorage()
        # file_path = fs.save(uploaded_file.name, uploaded_file)
        # file_url = fs.path(file_path)

        try:
            df = pd.read_excel(uploaded_file)
            # df = pd.read_excel(file_url, parse_dates=['Posting Date', 'Due Date', 'Document Date', 'GRN Date'])
            # print(df['Posting Date'].head())
           
            if df.empty:
                context["message"] = "No data in Open GRN report."
            else:
               
                df['Posting Date'] = df['Posting Date'].dt.strftime('%Y-%m-%d')
                df['Due Date'] = df['Due Date'].dt.strftime('%Y-%m-%d')
                df['Document Date'] = df['Document Date'].dt.strftime('%Y-%m-%d')
                context["data"] = df.values.tolist()
                context["columns"] = df.columns.tolist()
                # Store DataFrame values and columns in the session
                request.session['data'] = df.values.tolist()
                request.session['columns'] = df.columns.tolist()
                
                
                
        except Exception as e:
            context["message"] = f"Error processing file: {e}"
        finally:
            pass
            # os.remove(file_url)

    elif request.method == 'POST' and request.POST.get('save_data') == 'true':
        # Handle save request
        # print('this-1')
        try:
            df_data = request.session.get('data')
            df_columns = request.session.get('columns')
            if df_data and df_columns:
                # print('this---1')
                df = pd.DataFrame(df_data, columns=df_columns)
                # print(save_folder)
                save_path = os.path.join(save_folder, "Open_GRN_Data.csv")
                df.to_csv(save_path, index=False)
                # print('this---2')
                # Redirect to home with success message indicator
                context["message"] = "GRN DATA saved successfully!"
            else:
                context["message"] = "No data available to save."
        except Exception as e:
            print(f"Error saving data: {e}")
            context["message"] = f"Error saving data: {e}"

        # Redirect to the home page
        return redirect('home')  # Replace 'home' with the name of your home page view

    return render(request, 'upload_opengrn.html', context)



