# actions/actions.py
import json
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, UserUtteranceReverted
from typing import Any, Dict, List
from spellchecker import SpellChecker
from db_query import get_db_connection, fetch_menu_names_from_db, fetch_report_types_from_db

class ActionFetchMenuNames(Action):
    def name(self) -> str:
        return "action_fetch_menu_names"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        search_query = tracker.get_slot("search_query")
        print(f"Search query: {search_query}")

        if not search_query:
            dispatcher.utter_message(text="Please provide a search term to find menus.")
            return []

        spell = SpellChecker()
        spell.word_frequency.load_words(["admin"])
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

        search_query = synonyms.get(search_query.lower(), search_query)

        conn = get_db_connection()
        if not conn:
            dispatcher.utter_message(text="Sorry, I couldn't connect to the database. Please try again later.")
            return []

        try:
            results = fetch_menu_names_from_db(search_query, conn)  # Use the db_query function

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

        if report_preference:
            return_slots = [SlotSet("report_preference", None)]
            if not menu_name:
                dispatcher.utter_message(text="Please select a menu option first.")
                return return_slots

        elif not menu_name:
            dispatcher.utter_message(text="Please select a menu option first.")
            return []

        menu_name_lowercase = menu_name.strip().lower()

        if tracker.get_slot("menu_name") != menu_name:
            return [SlotSet("menu_name", menu_name), SlotSet("report_preference", None)]


        conn = get_db_connection()
        if not conn:
            dispatcher.utter_message(text="Sorry, I couldn't connect to the database. Please try again later.")
            return []

        try:
            results = fetch_report_types_from_db(menu_name_lowercase, conn)  # Use db_query function

            report_type_action_links = {}
            available_report_types = []
            menu_display_name = menu_name

            if results:
                menu_display_name = results[0][2] if results[0][2] else menu_name  # Use correct index
                for row in results:
                    report_type = row[0].strip().lower()
                    action_link = row[1]
                    if report_type and action_link:
                        report_type_action_links[report_type] = action_link
                        available_report_types.append(report_type)

            unique_report_types = sorted(list(set(available_report_types)))

            if report_preference:
                action_link = report_type_action_links.get(report_preference)
                if action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({report_preference.capitalize()})**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} ({report_preference.capitalize()})"
                    }

                    if "report" in report_preference.lower():
                        report_parts = action_link.split(",")
                        if len(report_parts) >= 3:
                            link_payload["report_name"] = report_parts[2].strip()

                    dispatcher.utter_message(json_message=json.loads(json.dumps(link_payload)))
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)]
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({report_preference}).")
                    return [SlotSet("report_preference", None)]

            elif len(unique_report_types) == 1:
                report_type = unique_report_types[0]
                action_link = report_type_action_links.get(report_type)
                if action_link:
                    link_payload = {
                        "type": "link",
                        "message": f"Opening **{menu_display_name} ({report_type.capitalize()})**...",
                        "link_url": action_link,
                        "link_text": f"Go to {menu_display_name} ({report_type.capitalize()})"
                    }

                    if "report" in report_type.lower():
                        report_parts = action_link.split(",")
                        if len(report_parts) >= 3:
                            link_payload["report_name"] = report_parts[2].strip()

                    dispatcher.utter_message(json_message=json.loads(json.dumps(link_payload)))
                    return [SlotSet("search_query", None), SlotSet("menu_name", None), SlotSet("report_preference", None)]
                else:
                    dispatcher.utter_message(text=f"Error: Action link not found for '{menu_display_name}' ({report_type}).")
                    return [SlotSet("report_preference", None)]

            elif len(unique_report_types) > 1:
                available_options = [rt.capitalize() for rt in unique_report_types]
                response_payload = {
                    "type": "confirmation",
                    "confirmation": available_options
                }

                dispatcher.utter_message(
                    text=f"For {menu_display_name}, please select an option:",
                    json_message=json.loads(json.dumps(response_payload))
                )
                return [SlotSet("report_preference", None)]
            else:
                dispatcher.utter_message(text=f"Sorry, no report options are available for **{menu_display_name}**.")
                return [SlotSet("report_preference", None)]


        except Exception as e:
            dispatcher.utter_message(text=f"Database error in ActionAskListOrCreate: {str(e)}")
            return [SlotSet("report_preference", None)]
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
    
class ActionUtterAskSearchTerm(Action):
    def name(self) -> str:
        return "action_utter_ask_search_term"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatcher.utter_message(
            text="Search for a term to get the list",
            json_message={
                "type": "text_popup",
                "menu_options": [
                    {"actions": ["Search for class"]},
                    {"actions": ["Find library"]},
                    {"actions": ["Look for attendance"]}
                ]
            }
        )
        return []