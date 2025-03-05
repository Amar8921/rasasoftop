# actions/actions.py
import json
import pyodbc
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted
from typing import Any, Dict, List
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
            "DATABASE=Pearl_2022_Staging;"
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


class ActionFetchMenuNames(Action):
    def name(self) -> str:
        return "action_fetch_menu_names"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        search_query = tracker.get_slot("search_query")

        if not search_query:
            dispatcher.utter_message(text="Please provide a search term to find menus.")
            return []

        spell = SpellChecker()
        corrected_query = spell.correction(search_query)

        if corrected_query and corrected_query != search_query:
            print(f"Corrected search query from: '{search_query}' to: '{corrected_query}'")
            search_query = corrected_query

        synonyms = {
            "present": "attendance", "absent": "attendance", "roll call": "attendance", "presence": "attendance",
            "bus": "transport", "vehicle": "transport", "transportation": "transport",
            "pupils": "student", "learners": "student", "children": "student",
            "record": "report", "data": "report"
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


class ActionAskListOrCreate(Action): # Or rename to ActionHandleMenuSelection
    def name(self) -> str:
        return "action_ask_list_or_create" # Or "action_handle_menu_selection"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        menu_name = tracker.get_slot("menu_name")
        report_preference = tracker.get_slot("report_preference") # Check if report_preference is already set

        if not menu_name:
            dispatcher.utter_message(text="Please select a menu option first.")
            return []

        menu_name_lowercase = menu_name.strip().lower()

        conn = get_db_connection() # Get database connection
        if not conn: # Check if connection was successful
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
            menu_display_name = menu_name # Default in case MenuName is not found in results

            if results:
                menu_display_name = results[0][2] if results[0][2] else menu_name
                for row in results:
                    report_type = row[0].strip().lower()
                    action_link = row[1]
                    if report_type and action_link:
                        report_type_action_links[report_type] = action_link
                        available_report_types.append(report_type)

            unique_report_types = sorted(list(set(available_report_types)))
            has_list = "list" in unique_report_types
            has_create = "create" in unique_report_types

            if report_preference: # User has already chosen "list" or "create"
                action_link = report_type_action_links.get(report_preference)
                if action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({report_preference.capitalize()})**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} ({report_preference.capitalize()})"
                    }
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)] # Clear report_preference slot as well
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({report_preference}).")
                    return []
            elif has_list and has_create:
                dispatcher.utter_message(
                    text=f"For **{menu_display_name}**, do you want to see a list or create?",
                    json_message={"type": "menu_options", "options": ["List", "Create"]}
                )
                return []
            elif has_list:
                report_type = "list"
                action_link = report_type_action_links.get(report_type)
                if action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} (List)**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} (List)"
                    }
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)] # Clear report_preference slot as well
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' (List).")
                    return []
            elif has_create:
                report_type = "create"
                action_link = report_type_action_links.get(report_type)
                if action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} (Create)**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} (Create)"
                    }
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)] # Clear report_preference slot as well
            elif unique_report_types: # Handle other report types if needed - currently defaults to first available
                default_report_type = unique_report_types[0]
                default_action_link = report_type_action_links.get(default_report_type)
                if default_action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({default_report_type.capitalize()})**...",
                        "link_url": default_action_link,
                        "link_text": f"Go to {menu_display_name} ({default_report_type.capitalize()})"
                    }
                    dispatcher.utter_message(json_message=link_payload)
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)] # Clear report_preference slot as well
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({default_report_type}).")
                    return []
            else:
                dispatcher.utter_message(text=f"Sorry, no report options are available for **{menu_display_name}**.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error in ActionAskListOrCreate: {str(e)}") # Or ActionHandleMenuSelection
        finally:
            if conn:
                conn.close()
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

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatcher.utter_message(
            text="Do you need a list?",
            json_message={
                "type": "confirmation",
                "confirmation": [{"choices": ["Yes", "No"]}]
            }
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