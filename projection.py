import creds
import gspread

from loguru import logger

# Connect to Google Sheets
gc = gspread.oauth(credentials_filename="C:\Scans\credentials.json",
                   authorized_user_filename="C:\Scans\\authorized_user.json")
spreadsheet = gc.open_by_key(creds.schedule_id)
sheet = spreadsheet.worksheet("6.16-6.21")

def main():
    """Posts hourly projections to slack
    Channel: Leadership-Team
    Frequency: Hourly
    """
    sales = sheet.acell("C12").value
    logger.info(f"Sales: {sales}")


if __name__ == "__main__":
    main()