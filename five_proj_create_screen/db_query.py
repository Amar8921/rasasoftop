# db_query.py
import pyodbc
import os  # Import the 'os' module
from dotenv import load_dotenv  # Import load_dotenv

load_dotenv()
# **Important Security Note:**
# NEVER hardcode database credentials! Use environment variables.
# This example uses environment variables for better security.
def get_db_connection():
    """Establishes a connection to the database using environment variables."""
    try:
        server = os.environ.get("DB_SERVER")
        database = os.environ.get("DB_DATABASE")
        username = os.environ.get("DB_USERNAME")
        password = os.environ.get("DB_PASSWORD")
        driver = os.environ.get("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")  # Default driver

        # Check if all required environment variables are set
        if not all([server, database, username, password]):
            raise ValueError("Missing database connection environment variables.")

        conn_str = (
            f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"
        )
        conn = pyodbc.connect(conn_str)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")  # Log the error
        return None



def fetch_menu_names_from_db(search_query, conn):
    """Fetches menu names from the database based on the search query."""
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
        return results
    except Exception as e:
        raise  # Re-raise the exception to be handled by the calling function


def fetch_report_types_from_db(menu_name_lowercase, conn):
    """Fetches report types and action links from the database for a given menu name."""
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
        return results
    except Exception as e:
        raise  # Re-raise the exception