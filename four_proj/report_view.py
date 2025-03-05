import os
import xml.etree.ElementTree as ET

def get_report_parameters_from_rdl(report_name, report_physical_path=None, hosting_environment_content_root_path=None):
    """
    Extracts report parameters from an RDL (Report Definition Language) file.
    ... (rest of the docstring is the same)
    """

    rdlc_file_path = ""
    print(f"get_report_parameters_from_rdl received report_name: '{report_name}'") # DEBUG: Print received report_name
    if report_physical_path:
        rdl_path = os.path.join(report_physical_path, f"{report_name}.rdl")
        print(f"rdl_path: '{rdl_path}'") # DEBUG: Print rdl_path
        if os.path.exists(rdl_path):
            rdlc_file_path = rdl_path
    elif hosting_environment_content_root_path:
        rdlc_file_path = os.path.join(hosting_environment_content_root_path, "Areas", "Reports", "RDL", f"{report_name}.rdl")
    else:
        raise ValueError("Either report_physical_path or hosting_environment_content_root_path must be provided.")

    print(f"rdlc_file_path: '{rdlc_file_path}'") # DEBUG: Print rdlc_file_path
    
    print(f"rdlc_file_path: '{rdlc_file_path}'") # DEBUG: Print rdlc_file_path
    print(f"Attempting to open RDL file at path: {rdlc_file_path}")

    print(f"Attempting to open RDL file at path: {rdlc_file_path}")
    if not os.path.exists(rdlc_file_path):
        print(f"RDL file not found at: {rdlc_file_path}")
        return []

    try:
        tree = ET.parse(rdlc_file_path)
        root = tree.getroot()
        namespaces = {'rdl': 'http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition'}

        report_parameters = []
        report_parameters_element = root.find("rdl:ReportParameters", namespaces)

        print(f"ReportParameters Element: {report_parameters_element}") # Keep debug print for element

        if report_parameters_element is not None:
            for param_element in report_parameters_element.findall("rdl:ReportParameter", namespaces):
                # Correctly extract Name from attribute, and Prompt from child element
                param_name = param_element.get('Name')  # <---- CHANGED LINE: Get attribute 'Name'
                prompt_element = param_element.find("rdl:Prompt", namespaces)

                param_prompt = prompt_element.text if prompt_element is not None else None

                report_parameters.append({'Name': param_name, 'Prompt': param_prompt})

        return report_parameters

    except ET.ParseError as e:
        print(f"Error parsing RDL file: {e}")
        return []


# --- Example Usage --- (rest of the example usage code remains the same)
report_name = "ClassWise3YearPerformanceReoport"
report_physical_path_setting = "C:/SOFTOP_PROJECTS/eduegateerpv1/Presentation/Eduegate.ERP.Admin/Reports/RDL"

report_params = get_report_parameters_from_rdl(report_name, report_physical_path=report_physical_path_setting)

if report_params:
    print("Report Parameters:")
    for param in report_params:
        print(f"  Name: {param['Name']}, Prompt: {param['Prompt']}")
else:
    print(f"No parameters found for report: {report_name} or RDL file not found.")


# def get_report_parameters_from_rdl2(report_name, report_physical_path=None, hosting_environment_content_root_path=None):
#     """
#     Extracts report parameters from an RDL (Report Definition Language) file.
#     ... (rest of the docstring remains the same)
#     """
#     rdlc_file_path = ""
#     print(f"get_report_parameters_from_rdl received report_name: '{report_name}'")  # DEBUG
#     if report_physical_path:
#         rdl_path = os.path.join(report_physical_path, f"{report_name}.rdl")
#         # replace \ with /
#         rdl_path = rdl_path.replace("\\", "/")
#         print(f"rdl_path (constructed): '{rdl_path}'")  # DEBUG: Print constructed rdl_path

#         print(f"Checking if path exists: '{rdl_path}'")  # DEBUG: Before exists() check
#         path_exists = os.path.exists(rdl_path)
#         print(f"os.path.exists('{rdl_path}') returned: {path_exists}")  # DEBUG: Result of exists()

#         if path_exists:
#             rdlc_file_path = rdl_path
#             print(f"rdlc_file_path set (path exists): '{rdlc_file_path}'") # DEBUG: When path exists
#         else:
#             print(f"Path DOES NOT EXIST: '{rdl_path}'") # DEBUG: When path DOES NOT exist

#     elif hosting_environment_content_root_path:
#         rdlc_file_path = os.path.join(hosting_environment_content_root_path, "Areas", "Reports", "RDL", f"{report_name}.rdl")
#     else:
#         raise ValueError("Either report_physical_path or hosting_environment_content_root_path must be provided.")

#     print(f"rdlc_file_path (after if block): '{rdlc_file_path}'")  # DEBUG: After if block
#     print(f"Attempting to open RDL file at path: {rdlc_file_path}")
#     if not os.path.exists(rdlc_file_path):
#         print(f"RDL file not found at: {rdlc_file_path}")
#         return []

#     try:
#         tree = ET.parse(rdlc_file_path)
#         root = tree.getroot()
#         namespaces = {'rdl': 'http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition'}

#         report_parameters = []
#         report_parameters_element = root.find("rdl:ReportParameters", namespaces)

#         print(f"ReportParameters Element: {report_parameters_element}")  # DEBUG
#         if report_parameters_element is not None:
#             for param_element in report_parameters_element.findall("rdl:ReportParameter", namespaces):
#                 param_name = param_element.get('Name')
#                 prompt_element = param_element.find("rdl:Prompt", namespaces)
#                 param_prompt = prompt_element.text if prompt_element is not None else None
#                 report_parameters.append({'Name': param_name, 'Prompt': param_prompt})
#         return report_parameters
#     except ET.ParseError as e:
#         print(f"Error parsing RDL file: {e}")
#         return []