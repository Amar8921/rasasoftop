import json
import pyodbc
import os
import xml.etree.ElementTree as ET
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FormValidation, FollowupAction, ActiveLoop, EventType, ActionExecuted
from typing import Any, Dict, List, Text, Optional
from rasa_sdk import Action
from rasa_sdk.events import UserUtteranceReverted
import requests
from spellchecker import SpellChecker  # Import SpellChecker


# Database connection function
def get_db_connection():
    conn = pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=192.168.29.100;"
        "DATABASE=Pearl_2022_Staging;"
        "UID=eduegateuser;"
        "PWD=eduegate@123"
    )
    return conn


def get_report_parameters_from_rdl(report_name, report_physical_path=None):
    """
    Extracts report parameters from an RDL file.
    """
    rdlc_file_path = ""
    print(f"get_report_parameters_from_rdl received report_name: '{report_name}'")
    if report_physical_path:
        rdl_path = os.path.join(report_physical_path, f"{report_name}.rdl")
        print(f"rdl_path: '{rdl_path}'")
        if os.path.exists(rdl_path):
            rdlc_file_path = rdl_path
    else:
        raise ValueError("report_physical_path must be provided.")

    print(f"rdlc_file_path: '{rdlc_file_path}'")
    
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
                param_name = param_element.get('Name')
                prompt_element = param_element.find("rdl:Prompt", namespaces)
                param_prompt = prompt_element.text if prompt_element is not None else None
                report_parameters.append({'Name': param_name, 'Prompt': param_prompt})

        return report_parameters

    except ET.ParseError as e:
        print(f"Error parsing RDL file: {e}")
        return []

class ActionFetchMenuNames(Action):
    def name(self):
        return "action_fetch_menu_names"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        search_query = tracker.get_slot("search_query")

        if not search_query:
            dispatcher.utter_message(text="Please provide a search term.")
            return []

        spell = SpellChecker()
        corrected_query = spell.correction(search_query)

        if corrected_query and corrected_query != search_query:
            print(f"Corrected search query from: '{search_query}' to: '{corrected_query}'")
            search_query = corrected_query
        else:
            print(f"No correction needed for search query: '{search_query}'")

        synonyms = {
            "fee": "fees","charges": "fees", "tuition": "fees","finance": "fees",
            "present": "attendance", "absent": "attendance", "roll call": "attendance", "presence": "attendance","participation": "attendance",
            "bus": "transport", "vehicle": "transport", "transportation": "transport", "travel": "transport", "commute": "transport","school bus": "transport",
            "pupils": "student", "learners": "student", "children": "student", "kids": "student", "scholars": "student",
            "record": "report", "data": "report","stats": "report", "statistics": "report"
        }

        if search_query.lower() in synonyms:
            original_query = search_query
            search_query = synonyms[search_query.lower()]
            print(f"Mapped synonym '{original_query}' to standard term '{search_query}'")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
            SELECT
                LEFT(ActionLink, CHARINDEX(',', ActionLink + ',') - 1) AS report_type,
                MenuName
            FROM setting.MenuLinks
            WHERE ActionLink LIKE ?
                AND ParentMenuID IS NOT NULL
                AND ActionLink IS NOT NULL
            ORDER BY report_type, MenuName;
            """
            cursor.execute(query, (f"%{search_query}%",))
            results = cursor.fetchall()
            conn.close()

            if results:
                grouped_menu_names = {}
                for row in results:
                    report_type = row[0].strip()
                    menu_name = row[1]
                    if report_type not in grouped_menu_names:
                        grouped_menu_names[report_type] = []
                    grouped_menu_names[report_type].append(menu_name)

                menu_names_list = []
                for report_type, menu_list in grouped_menu_names.items():
                    menu_names_list.append({report_type: menu_list})

                dispatcher.utter_message(
                    text="Here are the available options:",
                    json_message={
                        "type": "menu_popup",
                        "menu_names": menu_names_list
                    }
                )
                return [SlotSet("search_query", None)]
            else:
                dispatcher.utter_message(text="No menus found for your search.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error: {str(e)}")

        return []

class ActionFetchActionLink(Action):
    def name(self):
        return "action_fetch_action_link"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        menu_name = tracker.get_slot("menu_name")
        print(f"Received menu_name: {menu_name}")

        if not menu_name:
            dispatcher.utter_message(text="Please select a menu item.")
            return []

        menu_name_lowercase = menu_name.strip().lower()
        print(f"Processed menu_name: {menu_name_lowercase}")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT ActionLink, MenuName
                FROM setting.MenuLinks
                WHERE LOWER(MenuName) = ?
                AND ParentMenuID IS NOT NULL
                AND ActionLink IS NOT NULL;
            """
            cursor.execute(query, (menu_name_lowercase,))
            result = cursor.fetchone()
            conn.close()

            if result:
                action_link, full_menu_name = result
                # Extract report name (3rd part)
                try:
                    report_name = action_link.split(',')[2].strip()
                except IndexError:
                    dispatcher.utter_message(text=f"Could not extract report name from action link for '{menu_name}'.")
                    return []

                print(f"Extracted Report Name: {report_name}")
                return [
                    SlotSet("report_name", report_name),
                    SlotSet("menu_name", full_menu_name),  # Store the full menu name
                    FollowupAction("action_get_report_parameters"),
                ]
            else:
                dispatcher.utter_message(text=f"No action link found for '{menu_name}'.")
                return []

        except Exception as e:
            if conn:
                conn.rollback()
            dispatcher.utter_message(text=f"⚠ Database error: {str(e)}")
            return []

class ActionGetReportParameters(Action):
    def name(self) -> Text:
        return "action_get_report_parameters"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Gets the value of the report parameter from the user and stores it in the appropriate slot."""

        # Get the parameter value from the user's input (the 'inform' intent)
        parameter_value = tracker.latest_message.get("text")

        # Get the name of the parameter we asked for from the 'requested_slot'
        parameter_name = tracker.get_slot("requested_slot")

        if parameter_name and parameter_value:
            dispatcher.utter_message(text=f"Okay, I've saved {parameter_value} for {parameter_name}.")
            return [SlotSet(parameter_name, parameter_value), SlotSet("requested_slot", None)]  # Store the value and reset 'requested_slot'
        else:
            dispatcher.utter_message(text="I didn't receive a value for the parameter.")
            return []
        
class ActionAskReportParameter(Action):
    def name(self) -> Text:
        return "action_ask_report_parameter"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Asks for the next required report parameter."""

        report_name = tracker.get_slot("menu_name")  # Assuming you store the report name in this slot
        print(f"Report name: {report_name}")
        report_physical_path_setting = "C:/SOFTOP_PROJECTS/eduegateerpv1/Presentation/Eduegate.ERP.Admin/Reports/RDL" # Replace with ur path
        report_params = get_report_parameters_from_rdl(report_name, report_physical_path=report_physical_path_setting)

        if not report_params:
            dispatcher.utter_message(text="I couldn't find the report parameters.")
            return []

        # Get already provided parameters from tracker slots
        filled_slots = tracker.current_slot_values()
        print(f"Filled slots: {filled_slots}")

        # Find the next unfilled parameter
        next_parameter_to_ask = None
        for param in report_params:
            if param['Name'] not in filled_slots or filled_slots[param['Name']] is None:
                next_parameter_to_ask = param
                break

        if next_parameter_to_ask:
            dispatcher.utter_message(text=f"Please provide the value for {next_parameter_to_ask['Prompt']}:")
            return [SlotSet("requested_slot", next_parameter_to_ask['Name'])] # Set 'requested_slot' to the parameter name we are asking for
        else:
            # All parameters are filled
            dispatcher.utter_message(text="All required parameters have been provided.")
            #Potentially trigger the report generation action here
            return []
        
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

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain:Dict[Text, Any]):
        dispatcher.utter_message(
            text="Do you need a list?",
            json_message={
                "type": "conformation",
                "confirmation": [
                    {"choices": ["Yes", "No"]}
                ]
            }
        )
        return []

class ActionUtterINeedReportMenu(Action):
    def name(self) -> str:
        return "action_utter_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        dispatcher.utter_message(
            text="What do you want to do?",
            json_message={
                "type": "text_popup",
                "menu_options": [
                    {"actions": ["I need a report"]}
                ]
            }
        )
        return []
    
class ActionGenerateReport(Action):
    def name(self) -> Text:
        return "action_generate_report"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        report_name = tracker.get_slot("report_name")
        filled_slots = tracker.current_slot_values()
        report_params = {}

        # Get report parameters and path (same logic as in ActionAskReportParameter)
        report_physical_path_setting = "C:/SOFTOP_PROJECTS/eduegateerpv1/Presentation/Eduegate.ERP.Admin/Reports/RDL"  # Replace with your path!
        try:
            report_param_defs = get_report_parameters_from_rdl(report_name, report_physical_path=report_physical_path_setting)
            if not report_param_defs:
                dispatcher.utter_message(text=f"Could not retrieve parameters for report: {report_name}")
                return []
        except ValueError as e:  # Catch path error
            dispatcher.utter_message(text=str(e))
            return []

        # Build parameter dictionary, filtering out non-report parameters
        for param_def in report_param_defs:
            param_name = param_def['Name']
            if param_name in filled_slots:
                report_params[param_name] = filled_slots[param_name]

        # DEMO: Construct a message showing the parameters (instead of a real URL)
        param_message = ", ".join([f"{key}: {value}" for key, value in report_params.items()])
        dispatcher.utter_message(text=f"Report '{report_name}' generated successfully with parameters: {param_message}")

        return []