import pandas as pd
import os
from django.conf import settings
import json
from rapidfuzz import fuzz, process

def filingstatus(data):
    result = {}
    result1 = {}
    df = pd.DataFrame(data)
    df_3b = df[df['rtntype'] == 'GSTR3B']
    df_gstr1 = df[df['rtntype'] == 'GSTR1']
    # Convert 'dof' column to datetime format and # Sort by 'dof' in descending order
    df_gstr1.loc[:, 'dof'] = pd.to_datetime(df_gstr1['dof'], format='%d-%m-%Y')
    df_gstr1 = df_gstr1.sort_values(by='dof', ascending=False)
    # Take the top 3 rows
    top_3_rows_df_gstr1 = df_gstr1.head(3)
    if all(top_3_rows_df_gstr1['status'] == 'Filed'):
        result1['status'] = 'Filed'
        result1['month'] = top_3_rows_df_gstr1.iloc[0]['status']
        result1['month1'] = top_3_rows_df_gstr1.iloc[1]['status']
        result1['month2'] = top_3_rows_df_gstr1.iloc[2]['status']
    else:
        result1['status'] = 'Not Filed'
        result1['month'] = top_3_rows_df_gstr1.iloc[0]['status']
        result1['month1'] = top_3_rows_df_gstr1.iloc[1]['status']
        result1['month2'] = top_3_rows_df_gstr1.iloc[2]['status']
    # Convert 'dof' column to datetime format and # Sort by 'dof' in descending order
    df_3b.loc[:, 'dof'] = pd.to_datetime(df_3b['dof'], format='%d-%m-%Y')
    df_3b = df_3b.sort_values(by='dof', ascending=False)
    # Take the top 3 rows
    top_3_rows_df_gstr3b = df_3b.head(3)
    
    if all(top_3_rows_df_gstr1['status'] == 'Filed'):
        result['status'] = 'Filed'
        result['month'] = top_3_rows_df_gstr3b.iloc[0]['status']
        result['month1'] = top_3_rows_df_gstr3b.iloc[1]['status']
        result['month2'] = top_3_rows_df_gstr3b.iloc[2]['status']
    else:
        result['status'] = 'Not Filed'
        result['month'] = top_3_rows_df_gstr3b.iloc[0]['status']
        result['month1'] = top_3_rows_df_gstr3b.iloc[1]['status']
        result['month2'] = top_3_rows_df_gstr3b.iloc[2]['status']
    return result, result1, df_gstr1, df_3b

def Table_data(table,invoice_data):
    
    basic = invoice_data.get('SubTotal')
    Total = invoice_data.get('InvoiceTotal')
    tax = invoice_data.get('TotalTax')
    df = pd.DataFrame(table)
    check2 = {}
    check3 = {}
    # Columns to check
    required_columns = ['amount', 'qty_unitprice', 'qty_unit+rate_qty_unit', 'qty_unit+2_rate_qty_unit']

    # Find the first matching column
    present_columns = [col for col in required_columns if col in df.columns]

    if present_columns:
        first_present_col = present_columns[0]
        left_of_first = df.columns[df.columns.get_loc(first_present_col) - 1] if df.columns.get_loc(first_present_col) > 0 else None

        # Compute sums for the present columns
        sums = {col: df[col].sum() for col in present_columns}

        # Create a new row with sums and blanks for other columns
        new_row = {col: '' for col in df.columns}
        new_row.update(sums)
        if left_of_first:
            new_row[left_of_first] = 'Total->'

        # Append the new row
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    calculated_sum_check2 = float(df.at[len(df) - 1, 'qty_unitprice'])
        # Check specific columns for absolute difference with Total
    columns_to_check = ['qty_unit+rate_qty_unit', 'qty_unit+2_rate_qty_unit']
    for col in columns_to_check:
        if col in df.columns:
            # Get the calculated sum for this column (last row)
            calculated_sum = float(df.at[len(df) - 1, col])

            # Compare the absolute difference
            if abs(calculated_sum - float(Total)) > 1:
                # Drop the column
                df.drop(columns=[col], inplace=True)
            else:
                check3['OCR Captured Total Amount-->'] = Total
                check3[f'Calculated Total Amount-->[ Total of {col} column ]'] = calculated_sum
                check3['Check3'] = 'Okay'
        else:
            if abs(float(Total)-(calculated_sum_check2+float(tax))) < 1:
                check3['OCR Captured Total Amount-->'] = Total
                check3['OCR captured Total Tax'] = tax
                check3[f'Calculated Total Amount-->[ {tax} + {calculated_sum_check2} ]'] = float(tax)+calculated_sum_check2
                check3['Check3'] = 'Okay'
            else:
                check3['OCR Captured Total Amount-->'] = Total
                check3['OCR captured Total tax'] = tax
                check3[f'Calculated Total Amount-->[ {tax} {calculated_sum_check2} ]'] = float(tax)+calculated_sum_check2
                check3['Check3'] = 'Not Okay'
    calculated_sum_check2 = float(df.at[len(df) - 1, 'qty_unitprice'])
    if 'qty_unitprice' in df.columns and basic:
        if abs(calculated_sum_check2 - float(basic)) > 1:
            check2['OCR Captured Basic Amount-->'] = basic
            check2['Calculated Basic Amount-->[ Total of qty_unitprice column ]'] = calculated_sum_check2
            check2['Check2'] = 'Not Okay'
        else:
            check2['OCR Captured Basic Amount-->'] = basic
            check2['Calculated Basic Amount-->[ Total of qty_unitprice column ]'] = calculated_sum_check2
            check2['Check2'] = 'Okay'
        
    elif 'qty_unitprice' not in df.columns and basic:
        check2['OCR Captured Basic Amount-->'] = basic
        check2['Calculated Basic Amount-->[ Total of qty_unitprice column ]'] = 'Not calculated , Either Unit price or quantity is missing in table'
        check2['Check2'] = 'Not Confirmed, Please check , Either Unit price or quantity is missing in table'
    else:
        check2['OCR Captured Basic Amount-->'] = 'Basic amount not captured by OCR'
        check2['Calculated Basic Amount-->[ Total of qty_unitprice column ]'] = calculated_sum_check2
        check2['Check2'] = 'Not Confirmed, Please check'

    # Convert back to a list of dictionaries
    processed_list_of_dicts = df.to_dict(orient='records')


    # print(processed_list_of_dicts,check2,check3)
    return processed_list_of_dicts , check2 , check3

def InvoiceTable_vs_GrnTable(invoice_data,user_index):
    # print('this---1')
    table = invoice_data.get('Invoice items:')
    invoice_id = invoice_data.get('InvoiceId')
    # print('this---2')
    invoice_date = invoice_data.get('InvoiceDate')
    vendor_gst = invoice_data.get('Vendor Gst No.')
    df = pd.DataFrame.from_dict(table, orient='index')
    # print('this---3')
    if not df.empty:
        # Remove 'column_name' from its original position
        column_name = 'amount'
        # Insert 'column_name' at the last position
        try:
            col = df.pop(column_name)
            df['amount'] = col   
        except KeyError:
            print(f"Column '{column_name}' not found.")
        # print('this---4')
        df1 = df.to_dict(orient='records')
        df_ =  [200,df1]
    else:
        df_ =  [400,'No Table items in invoice']
    # path = 'GRN_DATA/Open_GRN_Data.csv'
    path = os.path.join(settings.BASE_DIR, 'GRN_Data', str(user_index), 'Open_GRN_Data.csv')
    # print('this---5')
    try:
        data = pd.read_csv(path)
        if invoice_id:
            invoice_id = str(invoice_id).lstrip('0')
        data = data[data['Supplier Ref No'] == invoice_id]
        # print(data)
        if not data.empty:
            # print('this---5')
            columns = ['Document Number','Supplier Ref No','Item No.', 'Item Description', 'Quantity', 'Price', 'Discount %', 'HSN/SAC', 'Total Before Discount']
            data = data[columns]
            # print(data)
            # Convert back to a list of dictionaries
            data1 = data.to_dict(orient='records')
            data_ = [200,data1]
        else:
            data_ = [400,'Invoice Id did not match with any record from OPEN GRN , Please Check']
    except:
        data_ = [400,'Please Upload Open GRN reports , found No Reports']
    # print(df_,data_)
    return df_,data_

def Invoicetable_vs_Grntable_compare(invoice_data,user_index):
    result = {}
    table = invoice_data.get('Invoice items:')
    invoice_id = invoice_data.get('InvoiceId')
    invoice_date = invoice_data.get('InvoiceDate')
    vendor_gst = invoice_data.get('Vendor Gst No.')
    supplier_name = invoice_data.get('VendorName') 
    Currency_Type = invoice_data.get('Currency')
    Discount_Amount = invoice_data.get('TotalDiscount')
    Total_Paymt_Due = invoice_data.get('InvoiceTotal')
    df = pd.DataFrame.from_dict(table, orient='index')
    # print('hello--1')
    if not df.empty:
        total_amount = df['amount'].sum()
    if not Total_Paymt_Due:
        Total_Paymt_Due = total_amount
   
    # path = 'GRN_DATA/Open_GRN_Data.csv'
    path = os.path.join(settings.BASE_DIR, 'GRN_Data', str(user_index), 'Open_GRN_Data.csv')
    print(path,invoice_id)
    try:
        data = pd.read_csv(path)
        if invoice_id:
            invoice_id = str(invoice_id).lstrip('0')
        data = data[data['Supplier Ref No'] == invoice_id]
        # print(data)
        if not data.empty:
            data_ = data.iloc[0]
            invoice_id_grn = data_['Supplier Ref No']
            supplier_name_grn = data_['Customer/Supplier Name']
            Currency_Type_grn = data_['Currency Type']
            if Currency_Type_grn == 'INR':
                Total_Paymt_Due_grn = data_['Total Paymt Due']  # Total Paymt Due  Total Paymt Due
            else:
                Total_Paymt_Due_grn = data_['Total Payment Due FC']
            # print(Total_Paymt_Due_grn)
            # print(Total_Paymt_Due)     
            # print('hello--3')  
        # print('hello--2')
    except Exception as e:
        # Print the error message
        print(f"Error: {str(e)}")
        data_ = [400,'Please Upload Open GRN reports , found No Reports']
    invoice_dict = {}
    supplier_name_dict = {}
    Currency_Type_dict = {}
    Total_Paymt_Due_dict = {}
    if invoice_id == invoice_id_grn:
        invoice_dict['Particulars'] = 'Supplier Ref No'
        invoice_dict['As_per_invoice'] = invoice_id
        invoice_dict['As_per_grn'] = invoice_id_grn
        invoice_dict['result'] = 'Matched'
    else:
        invoice_dict['Particulars'] = 'Supplier Ref No'
        invoice_dict['As_per_invoice'] = invoice_id
        invoice_dict['As_per_grn'] = invoice_id_grn
        invoice_dict['result'] = 'Not Matched'

    # supplier_name_ratio = fuzz.token_set_ratio(supplier_name.upper(), supplier_name_grn)
    # Normalize both strings to lowercase
    supplier_name_normalized = supplier_name.lower()
    supplier_name_grn_normalized = supplier_name_grn.lower()

    # Calculate token set ratio after normalization
    supplier_name_ratio = fuzz.token_set_ratio(supplier_name_normalized, supplier_name_grn_normalized)
    # print(supplier_name_ratio)
    if int(supplier_name_ratio) > 85:
        supplier_name_dict['Particulars'] = 'Supplier Name'
        supplier_name_dict['As_per_invoice'] = supplier_name
        supplier_name_dict['As_per_grn'] = supplier_name_grn
        supplier_name_dict['result'] = 'Matched'
    else:
        supplier_name_dict['Particulars'] = 'Supplier Name'
        supplier_name_dict['As_per_invoice'] = supplier_name
        supplier_name_dict['As_per_grn'] = supplier_name_grn
        supplier_name_dict['result'] = 'Not Matched'
    # print(supplier_name_dict)
    Currency_Type_ratio = fuzz.token_set_ratio(Currency_Type, Currency_Type_grn)
    if int(Currency_Type_ratio) > 95:
        Currency_Type_dict['Particulars'] = 'Currency Type'
        Currency_Type_dict['As_per_invoice'] = Currency_Type
        Currency_Type_dict['As_per_grn'] = Currency_Type_grn
        Currency_Type_dict['result'] = 'Matched'
    else:
        Currency_Type_dict['Particulars'] = 'Currency Type'
        Currency_Type_dict['As_per_invoice'] = Currency_Type
        Currency_Type_dict['As_per_grn'] = Currency_Type_grn
        Currency_Type_dict['result'] = 'Not Matched'
    # print(Currency_Type_dict)
    
    # print(type(Total_Paymt_Due),Total_Paymt_Due_grn)
    # print('hello---6')
    if abs(float(Total_Paymt_Due) - float(Total_Paymt_Due_grn)) < 1:
        Total_Paymt_Due_dict['Particulars'] = 'Total Paymt Due'
        Total_Paymt_Due_dict['As_per_invoice'] = Total_Paymt_Due
        Total_Paymt_Due_dict['As_per_grn'] = float(Total_Paymt_Due_grn)
        Total_Paymt_Due_dict['result'] = 'Matched'
    else:
        Total_Paymt_Due_dict['Particulars'] = 'Total Paymt Due'
        Total_Paymt_Due_dict['As_per_invoice'] = Total_Paymt_Due
        Total_Paymt_Due_dict['As_per_grn'] = Total_Paymt_Due_grn
        Total_Paymt_Due_dict['result'] = 'Not Matched'
    # print(Total_Paymt_Due_dict)
    result['invoice_id_match'] = invoice_dict
    result['supplier_name_match'] = supplier_name_dict
    result['Currency_Type_match'] = Currency_Type_dict
    result['Total_Paymt_Due_match'] = Total_Paymt_Due_dict
    # print(result)
    return result

def all_okay(api_response):
    
    result_ = {}
    status = 'All Okay'
    message = []
    try:
        # Check if the response file exists
        if api_response:
            
            result = api_response.get("result", {})
            # # print(result)
            # acount_check = result['CHECKS']['Account_check']
            # tax_check = result['CHECKS']['tax_check']
            # table_check = result['CHECKS']['table_data']['Table_Check_data']
            # invoice_data =  result['Invoice_data']

            # Safely get data, ensuring the expected types are returned
            acount_check = result.get('CHECKS', {}).get('Account_check', {})
            tax_check = result.get('CHECKS', {}).get('tax_check', {})
            table_check = result.get('CHECKS', {}).get('table_data', {}).get('Table_Check_data', [])
            invoice_data = result.get('Invoice_data', {})

            Complete_Invoice = acount_check['Complete_Invoice']['status']
            if Complete_Invoice == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Not a Complete_Invoice')

            Customer_Adress = acount_check['Customer_Adress']['status']
            if Customer_Adress == 'Matching':
                pass
            else:
                status = 'Not All Okay'
                message.append('Customer_Adress Not Matched')

            Customer_Name = acount_check['Customer_Name']['status']
            if Customer_Name == 'Matching':
                pass
            else:
                status = 'Not All Okay'
                message.append('Customer_Name Not Matched')

            Invoice_Blocked_Credit = acount_check['Invoice_Blocked_Credit']['status']
            if Invoice_Blocked_Credit == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice_Blocked_Credit Type')

            Invoice_Date = acount_check['Invoice_Date']['status']
            if Invoice_Date == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice_Date is not captured or not present')

            Invoice_Number = acount_check['Invoice_Number']['status']
            if Invoice_Number == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice_Number Not Captured or not present')

            Invoice_RCM_Services = acount_check['Invoice_RCM-Services']['status']
            if Invoice_RCM_Services == 'NO':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice_RCM-Services Type')

            Pre_year = acount_check['Pre_year']['status']
            if Pre_year == 'NO':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice is from Previous year')

            gstnumber_gstcharged = acount_check['gstnumber_gstcharged']['status']
            if gstnumber_gstcharged == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('gstnumber_gstcharged Not Okay')

            valid_invoice = acount_check['valid_invoice']['status']
            if valid_invoice == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Invoice is Invalid')

            ##Tax Check validations
            Company_Gst_Valid = tax_check['Company_Gst_Valid']['status']
            if Company_Gst_Valid == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Company_Gst_Valid')

            Company_Gst_mentioned = tax_check['Company_Gst_mentioned']['status']
            if Company_Gst_mentioned == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Company_Gst_mentioned')

            Vendor_206AB = tax_check['Vendor_206AB']['status']
            if Vendor_206AB == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_206AB')
            
            Vendor_Filing_status = tax_check['Vendor_Filing_status']['status']
            if Vendor_Filing_status == 'filled':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Filing_status')

            Vendor_Gst_Active = tax_check['Vendor_Gst_Active']['status']
            if Vendor_Gst_Active == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Gst not Active')

            Vendor_Gst_Valid = tax_check['Vendor_Gst_Valid']['status']
            if Vendor_Gst_Valid == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Gst inValid')

            Vendor_Gst_mentioned = tax_check['Vendor_Gst_mentioned']['status']
            if Vendor_Gst_mentioned == 'YES':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Gst not mentioned')

            Vendor_Pan_Adhar_Linked = tax_check['Vendor_Pan-Adhar_Linked']['status']
            if Vendor_Pan_Adhar_Linked == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Pan-Adhar not Linked')

            Vendor_Pan_Active = tax_check['Vendor_Pan_Active']['status']
            if Vendor_Pan_Active == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('Vendor_Pan not Active')
            
            tax_type_on_invoice = tax_check['tax_type_on_invoice']['status']
            if tax_type_on_invoice == 'Okay':
                pass
            else:
                status = 'Not All Okay'
                message.append('tax_type_on_invoice')

            ## Table checks

            parsed_data = json.loads(table_check)
            df = pd.DataFrame(parsed_data)
            if(df['check1'] == 'correct').all():
                Table_check1 = 'Okay'
            else:
                status = 'Not All Okay'
                message.append('Table_check1 not okay')
            
            basic_amount = invoice_data.get('SubTotal')
            if basic_amount:
                if 'qty_unitprice' in df.columns:
                    calculated_basic = df['qty_unitprice'].sum()
                    if abs(float(calculated_basic) - float(basic_amount)) < 1:
                        table_check2 = 'Okay'
                    else:
                        status = 'Not All Okay'
                        message.append('Table_Check2 not okay')
                elif 'amount' in df.columns:
                    calculated_basic = df['amount'].sum()
                    if abs(float(calculated_basic) - float(basic_amount)) < 1:
                        table_check2 = 'Okay'
                    else:
                        status = 'Not All Okay'
                        message.append('Table_Check2 not okay')
                else:
                    status = 'Not All Okay'
                    message.append('Table_Check2 not confirmed as amount or rate column in Invoice table')
            else:
                status = 'Not All Okay'
                message.append('Table_Check2 not confirmed as Basic amount was not captured by ocr for comprasion')
            result_['status'] = status
            result_['message'] = message
            # Update the "result" dictionary with the new key-value pair
            if "result" in api_response:
                api_response["result"]["Okay_NotOkay"] = result_
            else:
                # Create the "result" key if it doesn't exist
                api_response["result"] = {"Okay_NotOkay": result_}
            
            
            
            return result_,api_response
        else:
            result_['status'] = "No Response"
            result_['message'] = ''
            return result_

            
    except Exception as e:
        print(f"An error occurred: {e}")
        # print('No Response ',api_response)
    
    

data1 = [{'arn': 'AB291024101571O',
      'dof': '20-11-2024',
      'mof': 'ONLINE',
      'ret_prd': '102024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AB290824122786P',
      'dof': '20-09-2024',
      'mof': 'ONLINE',
      'ret_prd': '082024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AB290524227031I',
      'dof': '20-06-2024',
      'mof': 'ONLINE',
      'ret_prd': '052024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AB290924223742X',
      'dof': '19-10-2024',
      'mof': 'ONLINE',
      'ret_prd': '092024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AB290624128339U',
      'dof': '18-07-2024',
      'mof': 'ONLINE',
      'ret_prd': '062024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290724791055T',
      'dof': '17-08-2024',
      'mof': 'ONLINE',
      'ret_prd': '072024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290424766607P',
      'dof': '16-05-2024',
      'mof': 'ONLINE',
      'ret_prd': '042024',
      'rtntype': 'GSTR3B',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290924326972O',
      'dof': '09-10-2024',
      'mof': 'ONLINE',
      'ret_prd': '092024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290824262662U',
      'dof': '09-09-2024',
      'mof': 'ONLINE',
      'ret_prd': '082024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA291024214102X',
      'dof': '08-11-2024',
      'mof': 'ONLINE',
      'ret_prd': '102024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA2907242293441',
      'dof': '08-08-2024',
      'mof': 'ONLINE',
      'ret_prd': '072024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA2905242116738',
      'dof': '07-06-2024',
      'mof': 'ONLINE',
      'ret_prd': '052024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290624176046Z',
      'dof': '06-07-2024',
      'mof': 'ONLINE',
      'ret_prd': '062024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'},
     {'arn': 'AA290424140120R',
      'dof': '06-05-2024',
      'mof': 'ONLINE',
      'ret_prd': '042024',
      'rtntype': 'GSTR1',
      'status': 'Filed',
      'valid': 'Y'}]

data2 = [{'item_description': 'HSS Drill Bit 5.4mm', 'item_quantity': 5.0, 'unit_price': 102.2, 'product_code': '8207', 'tax_rate': 18, 'amount': 511.0, 'qty_unitprice': 511.0, 'qty_unit+rate_qty_unit': 602.98, 'qty_unit+2_rate_qty_unit': 694.96, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 5.5mm', 'item_quantity': 5.0, 'unit_price': 102.85, 'product_code': '8207', 'tax_rate': 18, 'amount': 514.25, 'qty_unitprice': 514.25, 'qty_unit+rate_qty_unit': 606.815, 'qty_unit+2_rate_qty_unit': 699.38, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 3.6mm', 'item_quantity': 20.0, 'unit_price': 47.92, 'product_code': '8207', 'tax_rate': 18, 'amount': 958.4, 'qty_unitprice': 958.4, 'qty_unit+rate_qty_unit': 1130.912, 'qty_unit+2_rate_qty_unit': 1303.424, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 3.7mm', 'item_quantity': 20.0, 'unit_price': 47.92, 'product_code': '8207', 'tax_rate': 18, 'amount': 958.4, 'qty_unitprice': 958.4, 'qty_unit+rate_qty_unit': 1130.912, 'qty_unit+2_rate_qty_unit': 1303.424, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 4.2mm', 'item_quantity': 10.0, 'unit_price': 69.62, 'product_code': '8207', 'tax_rate': 18, 'amount': 696.2, 'qty_unitprice': 696.2, 'qty_unit+rate_qty_unit': 821.516, 'qty_unit+2_rate_qty_unit': 946.832, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 4.3mm -', 'item_quantity': 10.0, 'unit_price': 69.62, 'product_code': '8207', 'tax_rate': 18, 'amount': 696.2, 'qty_unitprice': 696.2, 'qty_unit+rate_qty_unit': 821.516, 'qty_unit+2_rate_qty_unit': 946.832, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 2.4mm', 'item_quantity': 10.0, 'unit_price': 29.93, 'product_code': '8207', 'tax_rate': 18, 'amount': 299.3, 'qty_unitprice': 299.3, 'qty_unit+rate_qty_unit': 353.174, 'qty_unit+2_rate_qty_unit': 407.048, 'check1': 'correct'},
        {'item_description': 'HSS Drill Bit 2.5mm', 'item_quantity': 10.0, 'unit_price': 29.93, 'product_code': '8207', 'tax_rate': 18, 'amount': 299.3, 'qty_unitprice': 299.3, 'qty_unit+rate_qty_unit': 353.174, 'qty_unit+2_rate_qty_unit': 407.048, 'check1': 'correct'},
        {'item_description': 'Pop Rivit Gun', 'item_quantity': 1.0, 'unit_price': 950.0, 'product_code': '8405', 'tax_rate': 18, 'amount': 950.0, 'qty_unitprice': 950.0, 'qty_unit+rate_qty_unit': 1121.0, 'qty_unit+2_rate_qty_unit': 1292.0, 'check1': 'correct'}]

invoice_data__ = {'Bank_Details': {'Account_holder_name': 'AMITH INC.,', 'Bank_Account_No': None, 'Bank_Branch': 'PEENYA INDUS  ESTATE BANGALORE', 'Bank_Name': 'State Bank of India', 'Email': None, 'IFSC_Code': 'SBIN0003024', 'VendorAddress': '#21A, 3rd a cross potti gardens s.m. road bangalore 560, None, None, None, None'},
                 'BillingAddress': 'None, Mahadevapura, Bangalore, None, 560 048, None', 
                 'BillingAddressRecipient': 'Glodesi Technologies Pvt Ltd.,', 
                 'Currency': 'INR', 
                 'CustomerName': 'Glodesi Technologies Pvt Ltd.,', 
                 'Cutomer Gst No.': '29AAGCG0335D2ZX', 
                 'Invoice items:': {'item#1': {'amount': '2975.0', 'item_description': 'PRECOIL M2×0.4×1.5D (3mm)', 'item_quantity': 700.0, 'product_code': 'SDMC02.0150\n73181190', 'unit': 'nos', 'unit_price': '4.25'}, 
                                    'item#2': {'amount': '690.0', 'item_description': 'PRECOIL M3x0.5x1.5D (4.5mm)', 'item_quantity': 300.0, 'product_code': 'SDMC03.0150\n73181190', 'unit': 'nos', 'unit_price': '2.3'}, 
                                    'item#3': {'amount': '690.0', 'item_description': 'STI Tap M2x0.4 ET', 'item_quantity': 1.0, 'product_code': '82074090', 'unit': 'nos', 'unit_price': '690.0'}, 
                                    'item#4': {'amount': '500.0', 'item_description': 'PRECOIL Inserting Tool M2x0.4', 'item_quantity': 1.0, 'product_code': '82041110', 'unit': 'nos', 'unit_price': '500.0'}}, 
                'InvoiceDate': '2024-11-14', 
                'InvoiceId': '3385/24-25', 
                'InvoiceTotal': '5729.00', 
                'PurchaseOrder': '241100417-\n24351025', 
                'SubTotal': '4855.00', 
                'Tax Items': {'CGST': {'amount': '436.95'}, 'SGST': {'amount': '436.95'}}, 
                'TotalTax': '873.90', 
                'Vendor Gst No.': '29BCUPS8159M1Z7', 
                'VendorAddress': '#21A, 3rd a cross potti gardens s.m. road bangalore 560, None, None, None, None', 
                'VendorAddressRecipient': 'AMITH INC.,', 
                'VendorName': 'AMITH INC.,'}
if __name__ == "__main__":
    
    # filingstatus(data1)
    total = 6942.00
    bas = 5883.05
    InvoiceTable_vs_GrnTable(invoice_data__)