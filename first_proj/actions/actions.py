import pyodbc
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from typing import Any, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import UserUtteranceReverted
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

class ActionFetchMenuNames(Action):
    def name(self):
        return "action_fetch_menu_names"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain): # Remove Domain type hint
        search_query = tracker.get_slot("search_query")

        if not search_query:
            dispatcher.utter_message(text="Please provide a search term.")
            return []

        spell = SpellChecker() # Initialize SpellChecker
        corrected_query = spell.correction(search_query) # Correct the query

        if corrected_query and corrected_query != search_query: # Check if correction was made and is different
            print(f"Corrected search query from: '{search_query}' to: '{corrected_query}'") # Log correction
            search_query = corrected_query # Use corrected query for DB search
        else:
            print(f"No correction needed for search query: '{search_query}'") # Log no correction

        try:
            conn = get_db_connection() # Replace with your actual connection function
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
            cursor.execute(query, (f"%{search_query}%",)) # Use potentially corrected search_query
            results = cursor.fetchall()
            conn.close()

            if results:
                grouped_menu_names = {}
                for row in results:
                    report_type = row[0].strip() # added strip to remove whitespace
                    menu_name = row[1]
                    if report_type not in grouped_menu_names:
                        grouped_menu_names[report_type] = []
                    grouped_menu_names[report_type].append(menu_name)

                # Structure the data as a list of dictionaries for "menu_names"
                menu_names_list = []
                for report_type, menu_list in grouped_menu_names.items():
                    menu_names_list.append({report_type: menu_list})

                # Send a custom JSON payload with the nested structure
                dispatcher.utter_message(
                    text="Here are the available options:",  # Optional: Still send a text message
                    json_message={
                        "type": "menu_popup",  # Indicate this is a menu pop-up
                        "menu_names": menu_names_list # List of dictionaries as "menu_names"
                    }
                )
            else:
                dispatcher.utter_message(text="No menus found for your search.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error: {str(e)}")

        return []

# Assuming get_db_connection is defined elsewhere and works correctly

class ActionFetchActionLink(Action):
    def name(self):
        return "action_fetch_action_link"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        menu_name = tracker.get_slot("menu_name")
        # make to lower case
        menu_name = menu_name.lower()

        if not menu_name:
            dispatcher.utter_message(text="Please select a menu item.")
            return []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                        SELECT DISTINCT ActionLink
            FROM setting.MenuLinks
            WHERE LOWER(MenuName) LIKE LOWER(?)
            AND ParentMenuID IS NOT NULL
            AND ActionLink IS NOT NULL;
            """
            cursor.execute(query, (menu_name,))
            action_link_data = cursor.fetchone()
            conn.close()

            if action_link_data and action_link_data[0]:  # Check if action_link_data is not None and has a value
                action_link = action_link_data[0]

                # Create a structured JSON payload for the link
                link_payload = {
                    "type": "link",  # Indicate this is a link response
                    "message": f"Click here to go to {menu_name}:", # General message
                    "link_url": action_link,  # The actual URL
                    "link_text": menu_name  # Text to display for the link
                }
                dispatcher.utter_message(json_message=link_payload)  # Send JSON response

            else:
                dispatcher.utter_message(text="No action link found for that menu item.")

        except Exception as e:
            dispatcher.utter_message(text=f"Database error: {str(e)}")

        return []

class ActionDefaultFallback(Action):
    """Executes the fallback action and goes back to the previous state of the dialogue"""

    def name(self) -> str:  # Updated Text -> str
        return "action_default_fallback"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:  # Updated Dict[Text, Any] -> Dict[str, Any]
        
        # Send a default response
        dispatcher.utter_message(response="utter_default")  # Use `response` instead of `template`

        # Revert the user's last message to keep conversation flow natural
        return [UserUtteranceReverted()]