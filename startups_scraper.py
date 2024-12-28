import os
import logging
import agentql
from agentql.ext.playwright.sync_api import Page
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from pyairtable import Api
import requests
import time

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Environment variables
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
os.environ["AGENTQL_API_KEY"] = os.getenv("AGENTQL_API_KEY")

G_USER = os.getenv("GOOGLE_MAIL")
G_PASS = os.getenv("GOOGLE_PASS")

AIRT_KEY = os.getenv("AIRTABLE_API_KEY")
AIRT_ID = os.getenv("AIRTABLE_BASE_ID")
AIRT_TABLE = os.getenv("AIRTABLE_TABLE_NAME")

# Initial URL
URL = "https://finder.startupnationcentral.org/startups/search?&days=30&sort=raised-desc&coretechnology=agxzfmlsbGlzdHNpdGVyJAsSF0Jhc2VDbGFzc2lmaWNhdGlvbk1vZGVsGICA4Lu1rJEIDA&status=Active&alltags=artificial-intelligence"

LOGIN_BTN = """
{
   login_btn
}

"""

LOGIN_QUERY = """
{
    username_field
    password_field
    sign_in_btn
}
"""
NEXT_PAGE = """
{
    pagination {
        next_page_btn(button with link to next page)
    }
    
}
"""

QUERY = """
{
    startup_list[]{
        Name(name of the company from the main table)
        Website(website links that contains '/company_page/')
        }       
}
    """

def login_input(page: Page):
    log.info("Logging in...")
    response = page.query_elements(LOGIN_BTN)
    response.login_btn.click()
    page.wait_for_page_ready_state()
    response = page.query_elements(LOGIN_QUERY)
    page.wait_for_page_ready_state()
    response.username_field.fill(G_USER)    
    response.password_field.fill(G_PASS)
    response.sign_in_btn.click()
    log.info("Logging is completed!")
    page.wait_for_page_ready_state()



def get_response(page: Page):
    """
    Query data using AgentQL and print the results.
    """
    log.info("Running AgentQL query...")
    response = page.query_data(QUERY)
    log.info("Query completed. Printing results:")
    print(response)
    return response

def get_to_next_page(page: Page):
    log.info("Moving to next page...")
    response = page.query_elements(NEXT_PAGE)
    response.pagination.next_page_btn.click()
    page.wait_for_page_ready_state()


def push_data_to_airtable(scraped_data):
    """
    Push scraped data to Airtable.

    Args:
        api_key (str): Airtable API Key.
        base_id (str): Airtable Base ID.
        table_name (str): Airtable Table Name.
        scraped_data (dict): Data to be uploaded in the format:
                             {"startup_list": [{"Name": "value", "Website": "value"}, ...]}
    """
    log.info("Connecting to Airtable...")
    # Airtable API endpoint
    url = f"https://api.airtable.com/v0/{AIRT_ID}/{AIRT_TABLE}"

    # Headers for Airtable API
    headers = {
        "Authorization": f"Bearer {AIRT_KEY}",
        "Content-Type": "application/json"
    }
    log.info("Connection to Airtable established...")
    log.info("Inserting data to Airtable...")
    # Transform the data for Airtable
    records = [{"fields": entry} for entry in scraped_data["startup_list"]]

    # Send data to Airtable in batches of up to 10 records
    batch_size = 10
    for i in range(0, len(records), batch_size):
        batch = {"records": records[i:i + batch_size]}
        response = requests.post(url, json=batch, headers=headers)

        # Check response status
        if response.status_code == 200:
            print(f"Batch {i // batch_size + 1} uploaded successfully.")
        else:
            print(f"Error uploading batch {i // batch_size + 1}: {response.json()}")
            return False  # Exit on error

        # Avoid hitting Airtable rate limits
        time.sleep(0.2)

    print("All data uploaded successfully.")
    return True



def main():
    """
    Launch Playwright, navigate to the page, and run the AgentQL query.
    """
    with sync_playwright() as p, p.chromium.launch(headless=False) as browser:
        # Create a new browser page and wrap it for AgentQL querying
        log.info("Launching browser...")
        page = agentql.wrap(browser.new_page())

        log.info(f"Navigating to {URL}...")
        page.goto(URL)

        login_input(page)

        # Execute the AgentQL query
        
        # Move to next page
        
        #get_response(page)
        page.wait_for_page_ready_state()
        
        status = True
        while status:
            current_url = page.url
            print(current_url)
            company_data = page.query_data(QUERY)
            push_data_to_airtable(company_data)

            get_to_next_page(page)
            page.wait_for_page_ready_state()
            print(current_url)
            if current_url == page.url:
                status = False

        page.close()





if __name__ == "__main__":
    main()
