import json
import pyodbc
import os
import xml.etree.ElementTree as ET
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted, FollowupAction
from typing import Any, Dict, List, Text
from spellchecker import SpellChecker

# **Important Security Note:**
# NEVER hardcode database credentials in your code, especially in production!
# Use environment variables, secure configuration files, or a secrets management system.
# The following `get_db_connection` function is for example purposes only and is INSECURE.

def get_db_connection():
    """
    **INSECURE EXAMPLE - DO NOT USE IN PRODUCTION**
    Establishes a database connection using hardcoded credentials.
    Replace with secure credential management in a real application.
    """
    try:
        conn = pyodbc.connect(
            "DRIVER={SQL Server};"
            "SERVER=192.168.29.100;"
            "DATABASE=Pearl_Staging;"
            "UID=eduegateuser;"
            "PWD=eduegate@123"
        )
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        if sqlstate == '28000':
            print("Database connection failed: Incorrect username or password.")
        else:
            print(f"Database connection error: {ex}")
        return None # Return None to indicate connection failure


def get_report_parameters_from_rdl(report_name, report_physical_path=None):
    """
    Extracts report parameters from an RDL (Report Definition Language) file.
    """
    rdlc_file_path = ""
    print(f"get_report_parameters_from_rdl received report_name: '{report_name}'")
    
    if report_physical_path:
        rdl_path = os.path.join(report_physical_path, f"{report_name}.rdl")
        print(f"rdl_path: '{rdl_path}'")
        if os.path.exists(rdl_path):
            rdlc_file_path = rdl_path
    else:
        # Default path - you should update this to match your environment
        rdlc_file_path = os.path.join("C:/SOFTOP_PROJECTS/eduegateerpv1/Presentation/Eduegate.ERP.Admin/Reports/RDL", f"{report_name}.rdl")
    
    print(f"rdlc_file_path: '{rdlc_file_path}'")
    
    if not os.path.exists(rdlc_file_path):
        print(f"RDL file not found at: {rdlc_file_path}")
        # Mock return for testing if file doesn't exist
        return [
            {'Name': 'ClassID', 'Prompt': 'Select Class', 'Type': 'dropdown'},
            {'Name': 'AcademicYear', 'Prompt': 'Select year', 'Type': 'dropdown'},
        ]

    try:
        tree = ET.parse(rdlc_file_path)
        root = tree.getroot()
        namespaces = {'rdl': 'http://schemas.microsoft.com/sqlserver/reporting/2016/01/reportdefinition'}

        report_parameters = []
        report_parameters_element = root.find("rdl:ReportParameters", namespaces)

        if report_parameters_element is not None:
            for param_element in report_parameters_element.findall("rdl:ReportParameter", namespaces):
                param_name = param_element.get('Name')
                prompt_element = param_element.find("rdl:Prompt", namespaces)
                param_prompt = prompt_element.text if prompt_element is not None else param_name
                
                # Determine parameter type (could be extended with more logic)
                param_type = 'text'  # Default type
                if 'date' in param_name.lower() or 'time' in param_name.lower():
                    param_type = 'date'
                elif 'id' in param_name.lower() and not ('idea' in param_name.lower() or 'identify' in param_name.lower()):
                    param_type = 'dropdown'

                report_parameters.append({
                    'Name': param_name, 
                    'Prompt': param_prompt, 
                    'Type': param_type
                })

        return report_parameters

    except ET.ParseError as e:
        print(f"Error parsing RDL file: {e}")
        # Return mock data for testing
        return [
            {'Name': 'ClassID', 'Prompt': 'Select Class', 'Type': 'dropdown'},
            {'Name': 'AcademicYear', 'Prompt': 'Select year', 'Type': 'dropdown'},
        ]
        


class ActionFetchMenuNames(Action):
    def name(self) -> str:
        return "action_fetch_menu_names"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        search_query = tracker.get_slot("search_query")

        if not search_query:
            dispatcher.utter_message(text="Please provide a search term to find menus.")
            return []

        spell = SpellChecker()
        spell.word_frequency.load_words(["admin"])  # Add "admin" to the spellchecker dictionary
        corrected_query = spell.correction(search_query)

        if corrected_query and corrected_query != search_query:
            print(f"Corrected search query from: '{search_query}' to: '{corrected_query}'")
            search_query = corrected_query

        synonyms = {
            "present": "attendance", "absent": "attendance", "roll call": "attendance", "presence": "attendance",
            "bus": "transport", "transportation": "transport",
            "pupils": "student", "learners": "student", "children": "student",
            "record": "report", "data": "report",
        }

        search_query = synonyms.get(search_query.lower(), search_query) # Use get with default value

        conn = get_db_connection() # Get database connection
        if not conn: # Check if connection was successful
            dispatcher.utter_message(text="Sorry, I couldn't connect to the database. Please try again later.")
            return []

        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    DISTINCT MenuName,
                    LEFT(ActionLink, CHARINDEX(',', ActionLink + ',') - 1) AS report_type
                FROM setting.MenuLinks
                WHERE ActionLink LIKE ?
                    AND ParentMenuID IS NOT NULL
                    AND ActionLink IS NOT NULL

                UNION ALL

                SELECT
                    DISTINCT MenuName,
                    LEFT(ActionLink1, CHARINDEX(',', ActionLink1 + ',') - 1) AS report_type
                FROM setting.MenuLinks
                WHERE ActionLink1 LIKE ?
                    AND ParentMenuID IS NOT NULL
                    AND ActionLink1 IS NOT NULL

                ORDER BY report_type, MenuName;
            """
            cursor.execute(query, (f"%{search_query}%", f"%{search_query}%"))
            results = cursor.fetchall()

            if results:
                grouped_menu_names = {}
                for row in results:
                    menu_name = row[0]
                    report_type = row[1].strip()
                    grouped_menu_names.setdefault(report_type, []).append(menu_name)

                menu_names_list = [{report_type: menu_list} for report_type, menu_list in grouped_menu_names.items()]
                dispatcher.utter_message(
                    text="Here are the available options:",
                    json_message={
                        "type": "menu_popup",
                        "menu_names": menu_names_list
                    }
                )
                return [SlotSet("search_query", None)]
            else:
                dispatcher.utter_message(text="No menus found for your search term.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error while fetching menus: {str(e)}")
        finally:
            if conn:
                conn.close()
        return []


class ActionAskListOrCreate(Action):
    def name(self) -> str:
        return "action_ask_list_or_create"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        menu_name = tracker.get_slot("menu_name")
        report_preference = tracker.get_slot("report_preference")

        if not menu_name:
            dispatcher.utter_message(text="Please select a menu option first.")
            return []

        menu_name_lowercase = menu_name.strip().lower()

        if tracker.get_slot("menu_name") != menu_name:
            return [SlotSet("menu_name", menu_name)]

        conn = get_db_connection()
        if not conn:
            dispatcher.utter_message(text="Sorry, I couldn't connect to the database. Please try again later.")
            return []

        try:
            cursor = conn.cursor()
            query = """
                SELECT
                    LEFT(ActionLink, CHARINDEX(',', ActionLink + ',') - 1) AS report_type,
                    ActionLink,
                    MenuName
                FROM setting.MenuLinks
                WHERE LOWER(MenuName) = ?
                    AND ParentMenuID IS NOT NULL
                    AND ActionLink IS NOT NULL

                UNION ALL

                SELECT
                    LEFT(ActionLink1, CHARINDEX(',', ActionLink1 + ',') - 1) AS report_type,
                    ActionLink1 AS ActionLink,
                    MenuName
                FROM setting.MenuLinks
                WHERE LOWER(MenuName) = ?
                    AND ParentMenuID IS NOT NULL
                    AND ActionLink1 IS NOT NULL;
            """
            cursor.execute(query, (menu_name_lowercase, menu_name_lowercase))
            results = cursor.fetchall()

            report_type_action_links = {}
            available_report_types = []
            menu_display_name = menu_name

            if results:
                menu_display_name = results[0][2] if results[0][2] else menu_name
                for row in results:
                    report_type = row[0].strip().lower()
                    action_link = row[1]
                    if report_type and action_link:
                        report_type_action_links[report_type] = action_link
                        available_report_types.append(report_type)

            unique_report_types = sorted(list(set(available_report_types)))

            # Check if any of the report types indicate this is a report
            is_report = any(rt in ['report', 'list'] for rt in unique_report_types)
            
            if report_preference:
                action_link = report_type_action_links.get(report_preference)
                if action_link:
                    # If this is a report and we're in create/view mode, check for parameters
                    if is_report and 'report' in action_link.lower():
                        # Extract report name from action link
                        # Assuming format like "Reports/ViewReport,ReportName"
                        parts = action_link.split(',')
                        if len(parts) > 1:
                            report_name = parts[2].strip()
                            
                            # Get report parameters
                            report_params = get_report_parameters_from_rdl(report_name)
                            
                            if report_params:
                                # Save params to a slot for later use
                                events = [
                                    SlotSet("report_name", report_name),
                                    SlotSet("report_params", report_params),
                                    SlotSet("report_action_link", action_link),
                                    SlotSet("current_param_index", 0)
                                ]
                                
                                # Start parameter collection process
                                return events + [FollowupAction("action_ask_report_parameter")]
                            
                    # If not a report or no parameters, just open the link
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({report_preference.capitalize()})**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} ({report_preference.capitalize()})"
                    }
                    link_payload = json.loads(json.dumps(link_payload))
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)]
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({report_preference}).")
                    return []
            elif len(unique_report_types) == 1:
                # If only one option is available, automatically proceed with it
                report_type = unique_report_types[0]
                action_link = report_type_action_links.get(report_type)
                if action_link:
                    # Check if this is a report and has parameters
                    if is_report and 'report' in action_link.lower():
                        # Extract report name from action link
                        parts = action_link.split(',')
                        if len(parts) > 1:
                            report_name = parts[1].strip()
                            
                            # Get report parameters
                            report_params = get_report_parameters_from_rdl(report_name)
                            
                            if report_params:
                                # Save params to a slot for later use
                                events = [
                                    SlotSet("report_name", report_name),
                                    SlotSet("report_params", report_params),
                                    SlotSet("report_action_link", action_link),
                                    SlotSet("current_param_index", 0)
                                ]
                                
                                # Start parameter collection process
                                return events + [FollowupAction("action_ask_report_parameter")]
                    
                    # If not a report or no parameters, just open the link
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({report_type.capitalize()})**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} ({report_type.capitalize()})"
                    }
                    link_payload = json.loads(json.dumps(link_payload))
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)]
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({report_type}).")
                    return []
            elif len(unique_report_types) > 1:
                available_options = [rt.capitalize() for rt in unique_report_types]
                
                response_payload = {
                    "type": "confirmation",
                    "confirmation": available_options
                }

                # Ensure proper JSON encoding
                dispatcher.utter_message(
                    text=f"For {menu_display_name}, please select an option:",
                    json_message=json.loads(json.dumps(response_payload))  # Ensure correct JSON format
                )
            else:
                dispatcher.utter_message(text=f"Sorry, no report options are available for **{menu_display_name}**.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error in ActionAskListOrCreate: {str(e)}")
        finally:
            if conn:
                conn.close()
        return []


class ActionAskReportParameter(Action):
    def name(self) -> str:
        return "action_ask_report_parameter"
        
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Get the necessary slots
        report_params = tracker.get_slot("report_params")
        current_param_index = tracker.get_slot("current_param_index") or 0
        param_values = tracker.get_slot("param_values") or {}
        
        # Check if we have parameters to collect
        if not report_params or current_param_index >= len(report_params):
            # All parameters collected, generate the report
            return [FollowupAction("action_generate_report")]
        
        # Get current parameter to collect
        current_param = report_params[current_param_index]
        param_name = current_param['Name']
        param_prompt = current_param['Prompt'] or f"Please enter {param_name}"
        param_type = current_param.get('Type', 'text')
        
        # For dropdown parameters, we would fetch options from the database
        # This is simplified here - in a real app, you'd query the DB for valid options
        if param_type == 'dropdown':
            # Example: querying options for a dropdown
            options = self.get_dropdown_options(param_name)
            
            if options:
                # Present dropdown options to user
                dropdown_payload = {
                    "type": "confirmation",
                    "confirmation": options
                }
                
                dispatcher.utter_message(
                    text=f"{param_prompt}:",
                    json_message=json.loads(json.dumps(dropdown_payload))
                )
            else:
                # Fallback to text input if no options found
                dispatcher.utter_message(text=f"{param_prompt}:")
        
        elif param_type == 'date':
            # For date parameters, inform user of expected date format
            dispatcher.utter_message(text=f"{param_prompt} (please enter in YYYY-MM-DD format):")
            
        else:
            # For regular text parameters
            dispatcher.utter_message(text=f"{param_prompt}:")
            
        # Return slot with current parameter name so we know which param the next user input belongs to
        return [SlotSet("current_param_name", param_name)]
    
    def get_dropdown_options(self, param_name):
        """Get dropdown options for a specific parameter type"""
        # This is a mock implementation - in a real system, you'd query your database
        options_map = {
            'ClassID': ['Class 1 - Meshaf', 'Class 2 - Meshaf'],
            'AcademicYear': ['2022-2023', '2023-2024']
        }
        
        # Return mapped options or an empty list if none defined
        return options_map.get(param_name, [])


class ActionSaveParameterValue(Action):
    def name(self) -> str:
        return "action_save_parameter_value"
        
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Get the necessary slots
        current_param_name = tracker.get_slot("current_param_name")
        current_param_index = tracker.get_slot("current_param_index") or 0
        param_values = tracker.get_slot("param_values") or {}
        
        # Get the user's input for the parameter value
        latest_message = tracker.latest_message
        param_value = latest_message.get('text', '')
        
        # Save the parameter value
        param_values[current_param_name] = param_value
        
        # Move to the next parameter
        next_param_index = current_param_index + 1
        
        # Return events to update slots and move to next parameter
        return [
            SlotSet("param_values", param_values),
            SlotSet("current_param_index", next_param_index),
            SlotSet("current_param_name", None),
            FollowupAction("action_ask_report_parameter")
        ]


class ActionGenerateReport(Action):
    def name(self) -> str:
        return "action_generate_report"
        
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Get all the collected information
        report_name = tracker.get_slot("report_name")
        action_link = tracker.get_slot("report_action_link")
        param_values = tracker.get_slot("param_values") or {}
        
        if not report_name or not action_link:
            dispatcher.utter_message(text="I'm sorry, but I couldn't find the report information.")
            return []
        
        # Build the URL with parameters
        # In a real app, you would construct the correct URL format for your report viewer
        url = action_link
        param_string = "&".join([f"{key}={value}" for key, value in param_values.items()])
        
        if '?' in url:
            url += f"&{param_string}"
        else:
            url += f"?{param_string}"
        
        # Create a link payload with the report URL
        link_payload = {
            "type": "link",
            "message": f"Generating **{report_name}** report with your selected parameters...",
            "link_url": url,
            "link_text": f"View {report_name} Report"
        }
        
        # Generate the link
        dispatcher.utter_message(json_message=json.loads(json.dumps(link_payload)))
        
        # Clear all report-related slots
        return [
            SlotSet("report_name", None),
            SlotSet("report_params", None),
            SlotSet("report_action_link", None),
            SlotSet("current_param_index", None),
            SlotSet("current_param_name", None),
            SlotSet("param_values", None),
            SlotSet("search_query", None),
            SlotSet("menu_name", None),
            SlotSet("report_preference", None)
        ]


class ActionDefaultFallback(Action):
    def name(self) -> str:
        return "action_default_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        dispatcher.utter_message(response="utter_default")
        return [UserUtteranceReverted()]


class ActionUtterYesNoMenu(Action):
    def name(self) -> str:
        return "action_yes_no_list"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatcher.utter_message(
            text="Do you need a list?",
            json_message={"type": "confirmation", "confirmation": ["Yes", "No"]}
        )
        return []


class ActionUtterINeedReportMenu(Action):
    def name(self) -> str:
        return "action_utter_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatcher.utter_message(
            text="What do you want to do?",
            json_message={
                "type": "text_popup",
                "menu_options": [{"actions": ["I need a report"]}]
            }
        )
        return []