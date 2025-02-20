import pyodbc

# Database connection details (update these)
server = "192.168.29.100"
database = "Pearl_2022_Staging"
username = "eduegateuser"
password = "eduegate@123"

# Establish the connection
conn = pyodbc.connect(
    f"DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
)
cursor = conn.cursor()

# SQL Query
query = "SELECT MenuName FROM setting.MenuLinks  where ParentMenuID IS NOT NULL AND ActionLink IS NOT NULL"
cursor.execute(query)

# Fetch all menu names
menu_names = [row[0] for row in cursor.fetchall()]

# Save to a text file
with open("menu_names.txt", "w", encoding="utf-8") as file:
    for menu in menu_names:
        file.write(menu + "\n")

# Close connection
cursor.close()
conn.close()

print("Menu names saved successfully!")
