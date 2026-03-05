# scrape.py

# ------------------------- DEPENDENCIES ------------------------- #

import logging
import re
import requests
from bs4 import BeautifulSoup as bs
import unicodedata
from datetime import datetime
import json
import psycopg2
import sys
import os
import pandas as pd
import traceback
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

# ------------------------- LOGGING CONFIGURATION ------------------------- #

# 🔹 Setup logging (Avoids Unicode Errors on Windows)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("scrape.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to the .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '../project-root/server/.env')

# Load the env variables
load_dotenv(dotenv_path)
DATABASE_URL = os.getenv("DATABASE_URL")

# Debug check
if not DATABASE_URL:
    print("🚨 DATABASE_URL not found!")
else:
    print(f"✅ Loaded DATABASE_URL: {DATABASE_URL[:50]}...")

ssl_mode = "require"

# ------------------------- SETUP ------------------------- #

team_names = ['KRÜ', 'C9', 'G2', 'SEN', 'NRG', 'LEV', '100T', 'LOUD', 'EG', 'FUR', 'MIBR', '2G',
              'KC', 'GX', 'MKOI', 'TL', 'VIT', 'FNC', 'TH', 'FUT', 'BBL', 'M8', 'NAVI', 'APK',
              'GE', 'ZETA', 'TS', 'DRX', 'BME', 'TLN', 'T1', 'PRX', 'GEN', 'DFM', 'RRQ', 'NS',
              'EDG', 'BLG', 'XLG', 'TEC']

def extract_match_id(url):
    """
    Extracts the unique match ID from a VLR.gg match URL.
    Example URL: "https://www.vlr.gg/314625/sentinels-vs-100-thieves-champions-tour-2024-americas-stage-1-w1"
    Extracts: 314625
    """
    match = re.search(r'vlr.gg/(\d+)/', url)
    if match:
        return int(match.group(1))
    else:
        print(f"⚠️ Failed to extract match ID from URL: {url}")
        return None

def extract_event_and_round(url, event_slug):
    path = urlparse(url).path
    slug = path.split('/')[-1]

    # Ensure event_slug is in slug
    if event_slug in slug:
        # Format event name directly from slug
        event_tokens = event_slug.split('-')
        # Capitalize all parts (preserving acronyms like VCT)
        event_name = ' '.join(token.upper() for token in event_tokens)

        # Extract the round part after the event slug
        round_part = slug.split(event_slug + '-')[-1]  # e.g. 'w1'
        round_tokens = round_part.split('-')
        round_name = ' '.join(token.upper() if len(token) <= 3 else token.capitalize() for token in round_tokens)
    else:
        event_name = "UNKNOWN EVENT"
        round_name = "Unknown Round"

    print(event_name.strip())
    print(round_name.strip())

    return event_name.strip(), round_name.strip()

def normalize_team_name(name):
    """ Remove accents and normalize team names """
    return ''.join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')

def clean_text(text):
    text = re.sub(r'\s+', ' ', text).strip()  # Remove excessive whitespace
    text = re.sub(r'\s*PICK\s*', '', text, flags=re.IGNORECASE)  # Remove "PICK"
    return text

# ------------------------- DATABASE UTILITY ------------------------- #

def get_team_id(team_name):
    """ Fetch the correct team_id by normalizing the name first and log missing teams. """
    normalized_name = normalize_team_name(team_name)

    cursor = conn.cursor()
    cursor.execute("SELECT team_id FROM teams WHERE team_name = %s", (normalized_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    else:
        print(f"⚠️ WARNING: Team '{team_name}' (Normalized: '{normalized_name}') not found in database.")

        # 🚨 Log the missing team in `missing_teams` if it's not already logged
        cursor.execute("SELECT id FROM missing_teams WHERE normalized_name = %s", (normalized_name,))
        already_logged = cursor.fetchone()

        if not already_logged:
            cursor.execute("INSERT INTO missing_teams (team_name, normalized_name) VALUES (%s, %s)", 
                           (team_name, normalized_name))
            conn.commit()
            print(f"📌 Logged missing team: {team_name}")

        return None  # Return None so we can skip inserting the series/game

def get_latest_scraped_event_series(conn, region=None):
    """
    Retrieves the most recent series_id from the `event_series` table.
    If `region` is provided, it filters by region. Otherwise, it returns the global max.
    """
    cursor = conn.cursor()

    if region:
        cursor.execute("""
            SELECT MAX(series_id)
            FROM event_series
            WHERE region = %s;
        """, (region,))
    else:
        cursor.execute("""
            SELECT MAX(series_id)
            FROM event_series;
        """)

    latest_series = cursor.fetchone()

    if latest_series and latest_series[0]:
        label = f"for {region}" if region else "(global)"
        print(f"🔍 Latest Scraped Event Series ID {latest_series[0]} {label}")
        return latest_series[0]
    else:
        print("⚠️ No previous event data found, scraping all matches.")
        return None

def get_latest_game_id(conn):
    """
    Fetches the highest game_id from the player_stats table in PostgreSQL.

    Args:
        conn: PostgreSQL database connection object.
        
    Returns:
        int: The most recent game_id (or 1 if no games exist).
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(MAX(game_id), 1) FROM event_player_stats")  # ✅ Use COALESCE to return 1 if NULL
    latest_game_id = cursor.fetchone()[0]
    
    return latest_game_id  # ✅ Returns 1 if no games exist

def get_or_create_player_id(player_name, team_abrev, conn):
    """
    Fetches the player_id from the `player` table.
    If the player is missing, inserts them with `Unknown` role and returns the new player_id.

    Args:
        player_name (str): The player's name.
        team_abrev (str): The player's team abbreviation.
        conn: The PostgreSQL database connection object.

    Returns:
        int: The player's ID.
    """

    cursor = conn.cursor()

    # ✅ Check if the player already exists
    cursor.execute("SELECT player_id FROM event_player WHERE player_name = %s", (player_name,))
    result = cursor.fetchone()

    if result:
        return result[0]  # ✅ Return existing player_id

    # 🚨 Get `team_id` from `teams` table using `team_abrev`
    cursor.execute("SELECT team_id FROM teams WHERE team_abrev = %s", (team_abrev,))
    team_result = cursor.fetchone()

    if team_result:
        team_id = team_result[0]  # ✅ Use the found team_id
    else:
        print(f"⚠️ WARNING: No team_id found for abbreviation '{team_abrev}'. Inserting player with NULL team_id.")
        team_id = None  # Allow inserting player without a team

    # 🚨 Player not found! Insert them into `player` table with "Unknown" role.
    print(f"⚠️ Player '{player_name}' not found in database. Adding them now...")
    cursor.execute("""
        INSERT INTO event_player (player_name, team_id, role) 
        VALUES (%s, %s, %s)
        RETURNING player_id
    """, (player_name, team_id, "Unknown"))

    player_id = cursor.fetchone()[0]  # ✅ Get the newly inserted player_id
    conn.commit()

    return player_id  # ✅ Return new player_id

# ------------------------- MATCH FILTERING ------------------------- #

def filter_urls_by_latest_scrape(url_list, region):
    """
    Filters out matches that have already been scraped by checking match_id.
    """
    filtered_urls = []

    for url in url_list:
        match_id = extract_match_id(url)

        if match_id is None:
            continue  # Skip URLs that failed extraction

        print(f"\n🔍 Checking if match {match_id} should be scraped...")

        if is_match_scraped(match_id, conn):
            print(f"⏩ Skipping {url}, already scraped (or mistakenly detected as completed).")
        else:
            filtered_urls.append(url)

    if not filtered_urls:
        print(f"✅ All matches up-to-date for {region}. No new matches to scrape.")

    return filtered_urls

def is_match_scraped(match_id, conn):
    """
    Checks if a match has already been scraped using match_id.
    If the series is 1-1, the scraper should NOT skip it.
    """
    cursor = conn.cursor()

    # ✅ Fetch the series info from the database
    cursor.execute("SELECT series_id, num_maps FROM event_series WHERE match_id = %s", (match_id,))
    result = cursor.fetchone()

    if not result:
        print(f"✅ Match {match_id} has NOT been scraped yet. Adding to scrape queue.")
        return False  # ✅ Match has not been scraped yet, so we need to scrape it

    series_id, num_maps = result
    print(f"🔎 Match {match_id} exists in database as Series {series_id} with {num_maps} maps.")

    # ✅ Count how many maps each team has won
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS away_wins
        FROM event_games 
        WHERE series_id = %s
    """, (series_id,))
    home_wins, away_wins = cursor.fetchone() or (0, 0)

    print(f"   🏆 Home Wins: {home_wins} | Away Wins: {away_wins}")

    if home_wins == 3 or away_wins == 3:
        print(f"   ⏩ Skipping Match {match_id}, already fully scraped (BO5 Final Score: {home_wins}-{away_wins}).")
        return True

    # ✅ If either team has already won 2 maps, the series is **complete**.
    if (home_wins == 2 or away_wins == 2) and num_maps <= 3:
        print(f"   ⏩ Skipping Match {match_id}, already fully scraped (BO3 Final Score: {home_wins}-{away_wins}).")
        return True # ✅ The series is fully complete
    
    # ✅ If it's 1-1, the third map is still needed, so scrape it
    if home_wins == 1 and away_wins == 1:
        print(f"   ⚠️ Series {series_id} is tied 1-1. Waiting for a third map. NOT marked as complete.")
        return False  # 🚨 The series is NOT complete—scrape the third map

    print(f"   ✅ Match {match_id} is in progress. Adding to scrape queue.")
    return False  # ✅ Continue scraping because the series is still ongoing

def is_series_completed(series_id, conn):
    """
    Check if a series has a completed match score (2-0, 0-2, 2-1, or 1-2).
    If the score is 1-1, the series is NOT complete.
    """
    cursor = conn.cursor()

    # ✅ Count how many games exist for this series
    cursor.execute("SELECT COUNT(*) FROM event_games WHERE series_id = %s", (series_id,))
    num_maps = cursor.fetchone()[0]

    print(f"\n🔍 Checking if Series {series_id} is complete...")
    print(f"   ➡️ Total Maps Played: {num_maps}")

    # ✅ Count how many maps each team has won
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
            SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS away_wins
        FROM event_games 
        WHERE series_id = %s
    """, (series_id,))
    result = cursor.fetchone()
    
    home_wins, away_wins = result if result else (0, 0)

    print(f"   🏆 Home Wins: {home_wins} | Away Wins: {away_wins}")

    # ✅ Determine if the series is complete
    if num_maps >= 2:  # Series should have at least 2 maps
        if home_wins == 1 and away_wins == 1:
            # 🚨 If it's 1-1, we expect a third map, so it's NOT complete.
            print(f"   ⚠️ Series {series_id} is tied 1-1. Waiting for a third map. NOT marked as complete.")
            return False

        # ✅ If either team has won 2 maps, the series is complete
        if home_wins == 2 or away_wins == 2:
            print(f"   ✅ Series {series_id} is complete! Final score: {home_wins}-{away_wins}")
            return True

    print(f"   ⚠️ Series {series_id} is still in progress. Current score: {home_wins}-{away_wins}")
    return False

# def is_series_completed(series_id, conn):
#     """
#     Check if a BO5 series has a completed match score (e.g. 3-0, 3-1, 3-2, or 2-3).
#     If neither team has 3 wins yet, the series is NOT complete.
#     """
#     cursor = conn.cursor()

#     # ✅ Count how many games exist for this series
#     cursor.execute("SELECT COUNT(*) FROM event_games WHERE series_id = %s", (series_id,))
#     num_maps = cursor.fetchone()[0]

#     print(f"\n🔍 Checking if Series {series_id} is complete...")
#     print(f"   ➡️ Total Maps Played: {num_maps}")

#     # ✅ Count how many maps each team has won
#     cursor.execute("""
#         SELECT 
#             SUM(CASE WHEN home_score > away_score THEN 1 ELSE 0 END) AS home_wins,
#             SUM(CASE WHEN away_score > home_score THEN 1 ELSE 0 END) AS away_wins
#         FROM event_games 
#         WHERE series_id = %s
#     """, (series_id,))
#     result = cursor.fetchone()
    
#     home_wins, away_wins = result if result else (0, 0)

#     print(f"   🏆 Home Wins: {home_wins} | Away Wins: {away_wins}")

#     # ✅ Determine if the series is complete
#     if home_wins == 3 or away_wins == 3:
#         print(f"   ✅ Series {series_id} is complete! Final score: {home_wins}-{away_wins}")
#         return True

#     print(f"   ⚠️ Series {series_id} is still in progress. Current score: {home_wins}-{away_wins}")
#     return False

# ------------------------- SCRAPING & DATA EXTRACTION ------------------------- #

def scrape_over_data(url_list):
    all_dfs = {}  # Dictionary to store processed DataFrames for each URL

    for url in url_list:
        response = requests.get(url)
        if response.status_code == 200:
            soup = bs(response.content, 'html.parser')

            # Initialize lists to store DataFrames for each pass
            first_pass_dfs = []
            second_pass_dfs = []

            # Find all game divs
            game_divs = soup.find_all('div', class_='vm-stats-game')

            # First pass: Find initial tables
            for game_div in game_divs:
                table = game_div.find('table', class_='wf-table-inset mod-overview')

                if table:
                    # Extract table data into a DataFrame
                    table_data = []
                    rows = table.find_all('tr')
                    for row in rows:
                        row_data = [cell.text.strip() for cell in row.find_all(['td', 'th'])]
                        table_data.append(row_data)

                    # Convert table_data into a DataFrame and append to first_pass_dfs list
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])  # Assuming first row is header
                    first_pass_dfs.append(df)

            # Second pass: Find the next tables
            for game_div in game_divs:
                table = game_div.find('table', class_='wf-table-inset mod-overview')
                if table:
                    next_table = table.find_next('table', class_='wf-table-inset mod-overview')
                    if next_table:
                        # Extract table data into a DataFrame
                        table_data = []
                        rows = next_table.find_all('tr')
                        for row in rows:
                            row_data = [cell.text.strip() for cell in row.find_all(['td', 'th'])]
                            table_data.append(row_data)

                        # Convert table_data into a DataFrame and append to second_pass_dfs list
                        df = pd.DataFrame(table_data[1:], columns=table_data[0])  # Assuming first row is header
                        second_pass_dfs.append(df)

            # Process and clean DataFrames from both passes
            first_pass_cleaned = [clean_over_dataframe(df) for df in first_pass_dfs if not df.empty]
            second_pass_cleaned = [clean_over_dataframe(df) for df in second_pass_dfs if not df.empty]

            # Combine corresponding DataFrames from both passes
            combined_dfs = []
            min_length = min(len(first_pass_cleaned), len(second_pass_cleaned))
            for i in range(min_length):
                if first_pass_cleaned[i] is not None and second_pass_cleaned[i] is not None:
                    combined_df = pd.concat([first_pass_cleaned[i], second_pass_cleaned[i]], axis=0)
                    combined_dfs.append(combined_df)
                    combined_df.reset_index(inplace=True, drop=True)

            all_dfs[url] = combined_dfs

        else:
            print('Failed to retrieve the webpage. Status code:', response.status_code)

    return all_dfs

def scrape_name_agent_data(url_list):
    all_dfs = {}  # Dictionary to store processed DataFrames for each URL

    for url in url_list:
        response = requests.get(url)
        if response.status_code == 200:
            soup = bs(response.content, 'html.parser')

            # Initialize lists to store DataFrames for each pass
            first_pass_dfs = []
            second_pass_dfs = []

            # Find all game divs
            game_divs = soup.find_all('div', class_='vm-stats-game')

            # First pass: Find initial tables
            for game_div in game_divs:
                table = game_div.find('table', class_='wf-table-inset mod-overview')
                if table:
                    df = extract_table_data(table)
                    first_pass_dfs.append(df)

            # Second pass: Find the next tables
            for game_div in game_divs:
                table = game_div.find('table', class_='wf-table-inset mod-overview')
                if table:
                    next_table = table.find_next('table', class_='wf-table-inset mod-overview')
                    if next_table:
                        df = extract_table_data(next_table)
                        second_pass_dfs.append(df)

            # Process and clean DataFrames from both passes
            first_pass_cleaned = [clean_name_agent_dataframe(df) for df in first_pass_dfs if not df.empty]
            second_pass_cleaned = [clean_name_agent_dataframe(df) for df in second_pass_dfs if not df.empty]

            # Combine corresponding DataFrames from both passes
            combined_dfs = []
            min_length = min(len(first_pass_cleaned), len(second_pass_cleaned))
            for i in range(min_length):
                if first_pass_cleaned[i] is not None and second_pass_cleaned[i] is not None:
                    combined_df = pd.concat([first_pass_cleaned[i], second_pass_cleaned[i]], axis=0).reset_index(drop=True)
                    combined_dfs.append(combined_df)

            all_dfs[url] = combined_dfs

        else:
            print('Failed to retrieve the webpage. Status code:', response.status_code)

    return all_dfs

def extract_table_data(table):
    """Extracts player name and agent data from a given table."""
    table_data = []
    rows = table.find_all('tr')
    for row in rows:
        player_name_cell = row.find('td', class_='mod-player')
        agent_name_cell = row.find('td', class_='mod-agents')
        if player_name_cell and agent_name_cell:
            player_name = player_name_cell.text.strip()
            agent_name = agent_name_cell.img.get('title', 'Unknown Agent').strip() if agent_name_cell.img else 'Unknown Agent'
            table_data.append([player_name, agent_name])
    return pd.DataFrame(table_data, columns=['player_name', 'agent'])

def scrape_perf_data(url_list):
    all_dfs = {}  # Dictionary to store processed DataFrames for each URL

    for url in url_list:
        response = requests.get(url)
        if response.status_code == 200:
            soup = bs(response.content, 'html.parser')

            # Initialize lists to store DataFrames for each pass
            first_pass_dfs = []

            # Find all game divs
            game_divs = soup.find_all('div', class_='vm-stats-game')

            # First pass: Find initial tables
            for game_div in game_divs:
                table = game_div.find('table', class_='wf-table-inset mod-adv-stats')

                if table:
                    # Extract table data into a DataFrame
                    table_data = []
                    rows = table.find_all('tr')
                    for row in rows:
                        row_data = [cell.text.strip() for cell in row.find_all(['td', 'th'])]
                        table_data.append(row_data)

                    # Convert table_data into a DataFrame and append to first_pass_dfs list
                    df = pd.DataFrame(table_data[1:], columns=table_data[0])  # Assuming first row is header
                    first_pass_dfs.append(df)

            # Process and clean DataFrames from both passes
            first_pass_cleaned = [clean_perf_dataframe(df) for df in first_pass_dfs if not df.empty]

            # Combine corresponding DataFrames from both passes
            combined_dfs = []
            min_length = min(len(first_pass_cleaned), len(first_pass_cleaned))
            for i in range(min_length):
                if first_pass_cleaned[i] is not None:
                    combined_df = pd.concat([first_pass_cleaned[i]], axis=0)
                    combined_dfs.append(combined_df)
                    combined_df.reset_index(inplace=True, drop=True)

            all_dfs[url] = combined_dfs

        else:
            print('Failed to retrieve the webpage. Status code:', response.status_code)

    return all_dfs

def scrape_and_process_match_stats(match_url, team_names, start_game_id):
    """
    Scrapes and processes player stats for a given match URL.
    - Scrapes overview, agent, and performance data.
    - Processes each dataset.
    - Merges them into a final structured player stats DataFrame.
    - Handles missing data gracefully.

    Args:
        match_url (str): Base URL of the match (e.g., "https://www.vlr.gg/314622/cloud9-vs-leviat-n").
        team_names (list): List of team abbreviations for cleanup.

    Returns:
        pd.DataFrame: Cleaned and structured player stats DataFrame.
    """

    print(f"\n🔍 Scraping and Processing Stats for Game ID ({start_game_id})")

    # Generate URLs for each data category
    over_test_url = f"{match_url}/?game=all&tab=overview"
    perf_test_url = f"{match_url}/?game=all&tab=performance"

    # 1️⃣ Scrape and Process Overview Data
    print("\n🔍 Scraping Overview Data...")
    over_data = scrape_over_data([over_test_url])
    over_df = process_overview_data(over_data, team_names, start_game_id)

    # 2️⃣ Scrape and Process Agent Data
    print("\n🔍 Scraping Agent Data...")
    agent_data = scrape_name_agent_data([over_test_url])
    agents_df = process_agent_data(agent_data, team_names, start_game_id)

    # 3️⃣ Scrape and Process Performance Data
    print("\n🔍 Scraping Performance Data...")
    perf_data = scrape_perf_data([perf_test_url])
    perf_df = process_performance_data(perf_data, team_names, start_game_id)

    # 4️⃣ Merge Processed DataFrames
    print("\n🔗 Merging Player Stats...")
    final_stats_df = merge_player_stats(over_df, agents_df, perf_df)

    # 5️⃣ **Set game_id to the highest value in final_stats_df**
    if not final_stats_df.empty:
        max_game_id = final_stats_df["game_id"].max()
        game_id = max_game_id + 1  # Set to the next available game_id
    else:
        game_id = start_game_id + 1  # Increment normally if no data

    print(f"\n✅ Scraping and Processing Complete! Next game_id: {game_id}")
    return final_stats_df, game_id  # ✅ Now correctly returning the updated game_id

# ------------------------- DATA CLEANING & PROCESSING ------------------------- #

def remove_team_abbr_ovr(player_name, team_list):
    parts = player_name.rsplit(' ', 1)  # Split from the right by the last space
    if len(parts) == 2 and parts[1] in team_list:
        return parts[0]  # Return the player name without the team abbreviation
    return player_name  # Return unchanged if no valid abbreviation found

def remove_team_abbr_perf(player_name, team_list):
    for team in team_list:
        if player_name.endswith(team):
            return player_name[:-len(team)]  # Remove the abbreviation from the end
    return player_name  # Return unchanged if no abbreviation found

def clean_over_dataframe(df):
    if df.empty:
        return None
    
    df_copy = df.copy()

    # Rename the columns
    df_copy.columns = ['name', 'blank', 'rating', 'acs', 'kills', 'deaths', 'assists', 'k/d', 'KAST', 'adr', 'hs', 'fk', 'fd', 'fk/fd']

    # Clean the 'name' column
    df_copy['name'] = df_copy['name'].str.strip().str.replace('\t', '').str.replace('\n', '')

    # Drop all unneeded columns
    df_copy = df_copy.drop(columns=['blank', 'rating', 'acs', 'k/d', 'KAST', 'hs', 'fk/fd'])
    
    # Apply a lambda function to extract the first number from each cell
    df_copy['kills'] = df_copy['kills'].apply(lambda x: x.split('\n')[0] if x else None)

    # Use a try-except block to handle potential errors in 'deaths' column processing
    try:
        df_copy['deaths'] = df_copy['deaths'].apply(lambda x: int(re.findall(r'\d+', x)[0]) if x else None)
    except IndexError:
        df_copy['deaths'] = None  # Handle the error by assigning a default value

    df_copy['assists'] = df_copy['assists'].apply(lambda x: x.split('\n')[0] if x else None)
    df_copy['adr'] = df_copy['adr'].apply(lambda x: x.split('\n')[0] if x else None)
    df_copy['fk'] = df_copy['fk'].apply(lambda x: x.split('\n')[0] if x else None)
    df_copy['fd'] = df_copy['fd'].apply(lambda x: x.split('\n')[0] if x else None)

    return df_copy

def clean_name_agent_dataframe(df):
    if df.empty:
        return None

    df_copy = df.copy()

    # Clean the 'name' and 'agent' columns
    df_copy['player_name'] = df_copy['player_name'].str.strip().str.replace('\t', '').str.replace('\n', '')
    df_copy['agent'] = df_copy['agent'].str.strip().str.replace('\t', '').str.replace('\n', '')

    return df_copy

def clean_perf_dataframe(df):
    if df.empty:
        return None
    
    df_copy = df.copy()

    # Rename the columns
    df_copy.columns = ['name', 'blank', '2K', '3K', '4K', '5K', '1v1', '1v2', '1v3', '1v4', '1v5', 'ECON', 'PL', 'DE']
        
    # Clean the 'name' column safely
    df_copy['name'] = df_copy['name'].str.strip().str.replace('\t', '').str.replace('\n', '')

    # Drop unneeded columns
    df_copy.drop(columns=['blank', '2K', '3K', '4K', 'ECON', 'PL', 'DE'], inplace=True)

    # Apply lambda function to extract first number safely
    for col in ['1v1', '1v2', '1v3', '1v4', '1v5', '5K']:
        df_copy[col] = df_copy[col].apply(lambda x: x.split('\n')[0] if isinstance(x, str) else x)

    # Replace empty strings only in object (string) columns
    for col in df_copy.select_dtypes(include='object').columns:
        df_copy[col] = df_copy[col].replace("", "0")

    # Convert all numeric columns to integers
    numeric_cols = [col for col in df_copy.columns if col != 'name']
    for col in numeric_cols:
        df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0).astype(int)

    # Calculate total clutches
    df_copy['clutches'] = df_copy[['1v1', '1v2', '1v3', '1v4', '1v5']].sum(axis=1)

    # Drop individual clutch columns
    df_copy.drop(columns=['1v1', '1v2', '1v3', '1v4', '1v5'], inplace=True)

    return df_copy

def process_overview_data(data_frames, team_names, start_game_id):
    """
    Processes the scraped overview data:
    - Flattens and structures the DataFrame.
    - Removes duplicate DataFrames from the same match.
    - Assigns game IDs.
    - Cleans player names and extracts team abbreviations.
    
    Args:
        data_frames (dict): Dictionary of scraped overview DataFrames.
        team_names (list): List of team abbreviations for cleanup.
        start_game_id (int): Starting game ID for processing.
        
    Returns:
        pd.DataFrame: Cleaned and structured overview DataFrame.
    """

    # Create a list of new keys
    new_keys = [f'Series {i+1}' for i in range(len(data_frames))]

    # Create a new dictionary with updated keys
    re_dfs = dict(zip(new_keys, data_frames.values()))

    # Remove the second item from each list value if it exists
    for key in re_dfs:
        if len(re_dfs[key]) > 1:
            del re_dfs[key][1]  # Delete the second item (index 1)

    # Convert dictionary values to a list
    values_list = list(re_dfs.values())

    # Flatten the list of lists into a single list of DataFrames
    flattened_list = [item for sublist in values_list for item in sublist]
    
    # 🚨 Check if `flattened_list` is empty before assigning game_id
    if not flattened_list:
        print("⚠️ No overview data available. Returning an empty DataFrame.")
        return pd.DataFrame(columns=["game_id", "player_name", "team_abrev", "kills", "deaths", "assists", "adr", "fk", "fd"])

     # ✅ Ensure `start_game_id` is not None
    game_id = start_game_id if start_game_id is not None else 1  
    
    # Assign game IDs
    game_id = start_game_id
    for df in flattened_list:
        df['game_id'] = game_id
        game_id += 1

    # Concatenate all DataFrames into one
    concatenated_df = pd.concat(flattened_list, ignore_index=True)

    # Extract team abbreviation from the player name column
    concatenated_df['team_abrev'] = concatenated_df['name'].apply(lambda x: x.split()[-1])

    # Apply function to clean player names (remove team abbreviations)
    concatenated_df['name'] = concatenated_df['name'].apply(lambda x: remove_team_abbr_ovr(x, team_names))

    # Rename columns
    new_names = ['player_name', 'kills', 'deaths', 'assists', 'adr', 'fk', 'fd', 'game_id', 'team_abrev']
    concatenated_df.columns = new_names

    # Reorder columns
    new_order = ['game_id', 'player_name', 'team_abrev', 'kills', 'deaths', 'assists', 'adr', 'fk', 'fd']
    overview_df = concatenated_df[new_order]

    print(f"✅ Processed Overview Data - {len(overview_df)} rows")
    return overview_df

def process_agent_data(agent_data, team_names, start_game_id):
    """
    Processes the scraped agent data:
    - Flattens and structures the DataFrame.
    - Removes duplicate DataFrames from the same match.
    - Assigns game IDs.
    - Cleans player names by removing team abbreviations.

    Args:
        agent_data (dict): Dictionary of scraped agent selection DataFrames.
        team_names (list): List of team abbreviations for cleanup.
        start_game_id (int): Starting game ID for processing.

    Returns:
        pd.DataFrame: Cleaned and structured agent selection DataFrame.
    """

    # Create a list of new keys
    new_keys = [f'Series {i+1}' for i in range(len(agent_data))]

    # Create a new dictionary with updated keys
    re_dfs = dict(zip(new_keys, agent_data.values()))

    # Remove the second item from each list value if it exists
    for key in re_dfs:
        if len(re_dfs[key]) > 1:
            del re_dfs[key][1]  # Delete the second item (index 1)

    # Convert dictionary values to a list
    values_list = list(re_dfs.values())

    # Flatten the list of lists into a single list of DataFrames
    flattened_list = [item for sublist in values_list for item in sublist]

    # Assign game IDs
    game_id = start_game_id
    for df in flattened_list:
        df['game_id'] = game_id
        game_id += 1

    # Concatenate all DataFrames into one
    concatenated_df = pd.concat(flattened_list, ignore_index=True)

    # Clean player names by removing team abbreviations
    concatenated_df['player_name'] = concatenated_df['player_name'].apply(lambda x: remove_team_abbr_ovr(x, team_names))

    print(f"✅ Processed Agent Data - {len(concatenated_df)} rows")
    return concatenated_df

def process_performance_data(performance_data, team_names, start_game_id):
    """
    Processes the scraped performance data:
    - Flattens and structures the DataFrame.
    - Removes duplicate DataFrames from the same match.
    - Assigns game IDs.
    - Cleans player names by removing team abbreviations.
    - Handles cases where no performance data is available.

    Args:
        performance_data (dict): Dictionary of scraped performance DataFrames.
        team_names (list): List of team abbreviations for cleanup.
        start_game_id (int): Starting game ID for processing.

    Returns:
        pd.DataFrame: Cleaned and structured performance DataFrame.
    """

    # Check if performance_data is empty
    if not performance_data or all(len(v) == 0 for v in performance_data.values()):
        print("⚠️ No performance data available. Returning an empty DataFrame.")
        return pd.DataFrame(columns=["game_id", "player_name", "clutches", "aces"])

    # Remove duplicate DataFrames from each match
    for key in performance_data:
        if len(performance_data[key]) > 1:
            del performance_data[key][0]  # Delete the first item (index 0)

    # Convert dictionary values to a list
    values_list = list(performance_data.values())

    # Flatten the list of lists into a single list of DataFrames
    flattened_list = [item for sublist in values_list for item in sublist]

    # Check again if flattened_list is empty to avoid the ValueError
    if not flattened_list:
        print("⚠️ No performance data available after processing. Returning an empty DataFrame.")
        return pd.DataFrame(columns=["game_id", "player_name", "clutches", "aces"])

    # Assign game IDs
    game_id = start_game_id
    for df in flattened_list:
        df['game_id'] = game_id
        game_id += 1

    # Concatenate all DataFrames into one
    concatenated_df = pd.concat(flattened_list, ignore_index=True)

    # Clean player names by removing team abbreviations
    concatenated_df['name'] = concatenated_df['name'].apply(lambda x: remove_team_abbr_perf(x, team_names))

    # Rename columns
    new_names = ['player_name', 'aces', 'clutches', 'game_id']
    concatenated_df.columns = new_names

    # Reorder columns
    new_order = ['game_id', 'player_name', 'clutches', 'aces']
    performance_df = concatenated_df[new_order]

    print(f"✅ Processed Performance Data - {len(performance_df)} rows")
    return performance_df

def merge_player_stats(over_df, agents_df, perf_df):
    """
    Merges overview, agent, and performance DataFrames into the final player stats DataFrame.
    - Ensures numeric data types.
    - Removes games where all values are 0 (unfinished matches).
    - Calculates fantasy points.

    Args:
        over_df (pd.DataFrame): Processed overview DataFrame.
        agents_df (pd.DataFrame): Processed agent DataFrame.
        perf_df (pd.DataFrame): Processed performance DataFrame.

    Returns:
        pd.DataFrame: Merged and processed player stats DataFrame.
    """

    # Merge overview with agents
    all_stats_df = pd.merge(over_df, agents_df, on=['game_id', 'player_name'], how='left')

    # Merge with performance data
    all_stats_df = pd.merge(all_stats_df, perf_df, on=['game_id', 'player_name'], how='left')

    # Reorder columns to match `player_stats` table
    new_order = [
        'game_id', 'player_name', 'team_abrev', 'agent', 'kills', 'deaths', 'assists',
        'adr', 'fk', 'fd', 'clutches', 'aces'
    ]
    all_stats_df = all_stats_df[new_order]

    # Convert all necessary columns to numeric types
    numeric_cols = ["kills", "deaths", "assists", "adr", "fk", "fd", "clutches", "aces"]
    for col in numeric_cols:
        all_stats_df[col] = pd.to_numeric(all_stats_df[col], errors='coerce').fillna(0)

    # 🛑 Remove Unfinished Matches (All Zero Values)
    complete_games_df = all_stats_df[
        (all_stats_df[numeric_cols].sum(axis=1) > 0)  # Keep rows where at least one stat is nonzero
    ]

    # 🏆 Calculate Fantasy Points
    complete_games_df["points"] = (
        complete_games_df["kills"] * 2 +
        complete_games_df["deaths"] * -1 +
        complete_games_df["assists"] * 1 +
        complete_games_df["adr"] * 0.05 +
        complete_games_df["fk"] * 3 +
        complete_games_df["fd"] * -3 +
        complete_games_df["clutches"] * 3 +
        complete_games_df["aces"] * 5
    )

    print(f"✅ Merged Player Stats - {len(complete_games_df)} rows (Unfinished matches removed)")
    return complete_games_df

# ------------------------- INSERT DATA INTO DB ------------------------- #

def insert_player_stats(final_stats_df, conn):
    """
    Inserts player stats into the `player_stats` table.
    Automatically adds missing players to the `player` table.

    Args:
        final_stats_df (pd.DataFrame): The processed player stats DataFrame.
        conn: The database connection object.
    """

    cursor = conn.cursor()

    for _, row in final_stats_df.iterrows():
        # ✅ Get the series_id for the game_id
        cursor.execute("SELECT series_id FROM event_games WHERE game_id = %s", (row["game_id"],))
        series_id_result = cursor.fetchone()
        if series_id_result is None:
            print(f"⚠️ No series_id found for game_id {row['game_id']}. Skipping player: {row['player_name']}")
            continue
        series_id = series_id_result[0]

        # ✅ Get or create player_id
        player_id = get_or_create_player_id(row["player_name"], row["team_abrev"], conn)

        # ✅ Insert into `player_stats` table (Avoid duplicate stats)
        cursor.execute("""
            INSERT INTO event_player_stats (
                player_id, series_id, game_id, agent, kills, deaths, assists, 
                fk, fd, clutches, aces, adr, points
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (player_id, game_id) DO NOTHING
        """, (
            player_id, series_id, row["game_id"], row["agent"],
            row["kills"], row["deaths"], row["assists"], row["fk"], row["fd"], 
            row["clutches"], row["aces"], row["adr"], row["points"]
        ))

    conn.commit()
    print(f"✅ Inserted {len(final_stats_df)} player stats into the database (New Players Added).")

def extract_scores(url_list, event_slug, region):
    """
    Extract match scores and update the series with new games over time.
    """

    latest_series_id = get_latest_scraped_event_series(conn)

    for idx, url in enumerate(url_list):
        print(f"\n🔍 Checking Match {idx+1}/{len(url_list)}: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f'❌ Failed to retrieve {url}. Error: {e}')
            continue

        stage, round_name = extract_event_and_round(url, event_slug)
        print(f"📌 Extracted Stage: {stage} (Round: {round_name})")

        soup = bs(response.content, 'html.parser')
        game_divs = soup.find_all('div', class_='vm-stats-game')

        # Store match-level info for series table
        series_home_team, series_away_team = None, None
        game_data = []
        total_home_score = 0
        total_away_score = 0

        for game_idx, game_div in enumerate(game_divs):
            game_header = game_div.find('div', class_='vm-stats-game-header')
            if game_header:
                team_divs = game_header.find_all('div', class_='team')
                team_names, team_scores = [], []

                for div_team in team_divs:
                    team_name = clean_text(div_team.find('div', class_='team-name').text.strip())
                    team_score = div_team.find('div', class_='score').text.strip()
                    team_score = int(team_score) if team_score.isdigit() else None

                    team_names.append(team_name)
                    team_scores.append(team_score)

                if len(team_names) == 2:
                    home_team = team_names[0]
                    away_team = team_names[1]
                    home_score = team_scores[0]
                    away_score = team_scores[1]

                    total_home_score += home_score
                    total_away_score += away_score

                    series_home_team = home_team
                    series_away_team = away_team

                    map_div = game_header.find('div', class_='map')
                    map_name = clean_text(map_div.find('span').text.strip()) if map_div else "Unknown"

                    map_duration_div = game_header.find('div', class_='map-duration')
                    map_duration = clean_text(map_duration_div.text.strip()) if map_duration_div else "Unknown"

                    game_data.append({
                        'home_team': home_team,
                        'away_team': away_team,
                        'map_name': map_name,
                        'map_duration': map_duration,
                        'home_score': home_score,
                        'away_score': away_score
                    })

        # Compute Round Differences
        home_round_difference = total_home_score - total_away_score
        away_round_difference = total_away_score - total_home_score

        # ✅ Get Team IDs
        home_team_id = get_team_id(series_home_team)
        away_team_id = get_team_id(series_away_team)

        # 🚨 Skip the series if either team is missing
        if home_team_id is None or away_team_id is None:
            print(f"   ❌ Skipping series: {series_home_team} vs {series_away_team} - Missing team logged.")
            continue
            
        # ✅ Ensure at least one game is completed before inserting the series
        completed_games = [
            g for g in game_data
            if g['home_score'] is not None and g['away_score'] is not None and g['map_duration'] not in ["-", "", None]
        ]

        if not completed_games:
            print(f"   ⏩ Skipping series: {series_home_team} vs {series_away_team} (No completed games yet) (Region: {region})")
            continue  # 🚨 Skip inserting the series until a game is played

        match_id = extract_match_id(url)

        if match_id is None:
            print(f"❌ ERROR: Could not extract match_id from URL: {url}")
            continue  # 🚨 Skip this match to prevent errors

        print(f"🔍 Checking match_id: {match_id}")

        cursor.execute("""
            SELECT series_id FROM event_series WHERE match_id = %s
        """, (match_id,))
        existing_series = cursor.fetchone()

        if existing_series:
            series_id = existing_series[0]
            print(f"   🔄 Series {series_id} already exists. Updating round diffs...")

            # ✅ Just update the round difference and num_maps
            cursor.execute("""
                UPDATE event_series
                SET home_round_difference = %s,
                    away_round_difference = %s,
                    num_maps = %s
                WHERE series_id = %s
            """, (home_round_difference, away_round_difference, len(completed_games), series_id))

            print(f"   ✅ Series {series_id} updated with Match ID {match_id} (Region: {region})")

        else:
            # ✅ If series does not exist, insert it
            match_id = extract_match_id(url)

            print(f"\n💾 Inserting New Series: {series_home_team} vs {series_away_team} [{stage}: {round_name}] (Match ID: {match_id})")
            cursor.execute("""
                INSERT INTO event_series (home_team_id, away_team_id, home_round_difference, 
                                    away_round_difference, num_maps, region, match_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING series_id;  -- ✅ This ensures the inserted ID is returned
            """, (home_team_id, away_team_id, home_round_difference, 
                away_round_difference, 0, region, match_id))

            series_result = cursor.fetchone()  # ✅ Fetch result safely

            if series_result:
                series_id = series_result[0]  # ✅ Extract the actual ID
                print(f"   ✅ Series ID {series_id} created with Match ID {match_id} ({stage}: {round_name})")
            else:
                print(f"❌ ERROR: Failed to retrieve series_id for match {match_id}. Skipping...")
                continue  # 🚨 Skip further processing for this match

       # ✅ Now Insert Completed Games Only
        for game in game_data:
            home_team_id = get_team_id(game['home_team'])
            away_team_id = get_team_id(game['away_team'])

            if home_team_id and away_team_id:
                # 🚨 Ensure the game is completed before inserting
                if (
                    game['map_name'] == "TBD" or 
                    game['home_score'] is None or 
                    game['away_score'] is None or 
                    game['map_duration'] in ["-", "", None]  # ✅ New check for incomplete games
                ):
                    print(f"   ⏩ Skipping unfinished game: {game['home_team']} vs {game['away_team']} "
                          f"(Map: {game['map_name']}, No Score or No Map Duration) (Region: {region})")
                    continue  # 🚨 Skip this game

                # ✅ Check if the game already exists before inserting
                cursor.execute("""
                    SELECT COUNT(*) FROM event_games
                    WHERE series_id = %s AND map_name = %s AND home_team_id = %s AND away_team_id = %s
                """, (series_id, game['map_name'], home_team_id, away_team_id))

                existing_game = cursor.fetchone()[0]

                if existing_game > 0:
                    print(f"   ⏩ Skipping duplicate game: {game['map_name']} | {game['home_team']} vs {game['away_team']} (Region: {region})")
                else:
                    print(f"   🏆 Inserting Game: {game['map_name']} | {game['home_team']} vs {game['away_team']} ({stage}: {round_name})")
                    cursor.execute("""
                        INSERT INTO event_games (series_id, map_name, home_team_id, away_team_id, map_duration, home_score, away_score, region)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (series_id, game['map_name'], home_team_id, away_team_id, game['map_duration'], game['home_score'], game['away_score'], region))

                    game_id = cursor.lastrowid  # ✅ Get the newly inserted game's ID
                    print(f"      ✅ Game inserted successfully! (Region: {region})")

                    # ✅ After inserting a new game, update `num_maps` in the `series` table
                    cursor.execute("""
                        UPDATE event_series 
                        SET num_maps = (SELECT COUNT(*) FROM event_games WHERE series_id = %s) 
                        WHERE series_id = %s
                    """, (series_id, series_id))

                    # ✅ Confirm update
                    cursor.execute("""
                        SELECT num_maps FROM event_series WHERE series_id = %s
                    """, (series_id,))
                    updated_num_maps = cursor.fetchone()[0]

                    print(f"   🔄 Updated `num_maps` for Series {series_id}: {updated_num_maps} games recorded.")

    conn.commit()
    print("\n✅ Data successfully inserted/updated into series and games tables.")
    
# ------------------------- UPDATING STATS ------------------------- #

def aggregate_series_player_stats(conn):
    """
    Aggregates individual game stats into series-level stats.
    Inserts or updates the `series_player_stats` table only if the series is complete.
    Also updates `adjusted_points` after inserting/updating stats.

    Args:
        conn: The database connection object.
    """
    cursor = conn.cursor()

    # ✅ Aggregate player stats at the series level
    cursor.execute("""
        SELECT 
            ps.series_id,
            ps.player_id,
            COUNT(ps.game_id) AS series_maps,
            SUM(ps.kills) AS series_kills,
            SUM(ps.deaths) AS series_deaths,
            SUM(ps.assists) AS series_assists,
            SUM(ps.fk) AS series_fk,
            SUM(ps.fd) AS series_fd,
            SUM(ps.clutches) AS series_clutches,
            SUM(ps.aces) AS series_aces,
            AVG(ps.adr) AS avg_adr_per_series,
            SUM(ps.points) AS series_points
        FROM event_player_stats ps
        JOIN event_series s ON ps.series_id = s.series_id
        GROUP BY ps.series_id, ps.player_id
    """)

    series_stats = cursor.fetchall()

    # ✅ Insert or update aggregated stats into `series_player_stats`
    for row in series_stats:
        (series_id, player_id, series_maps, series_kills, series_deaths, series_assists, 
         series_fk, series_fd, series_clutches, series_aces, avg_adr_per_series, series_points) = row

        # ✅ Check if data already exists for this `series_id` & `player_id`
        cursor.execute("""
            SELECT 1 FROM event_series_player_stats WHERE series_id = %s AND player_id = %s
        """, (series_id, player_id))
        exists = cursor.fetchone()

        if exists:
            # ✅ Update existing entry
            cursor.execute("""
                UPDATE event_series_player_stats
                SET series_maps = %s, series_kills = %s, series_deaths = %s, series_assists = %s, 
                    series_fk = %s, series_fd = %s, series_clutches = %s, series_aces = %s, 
                    avg_adr_per_series = %s, series_points = %s, updated_at = NOW()
                WHERE series_id = %s AND player_id = %s
            """, (series_maps, series_kills, series_deaths, series_assists, series_fk, series_fd,
                  series_clutches, series_aces, avg_adr_per_series, series_points,
                  series_id, player_id))

        else:
            # ✅ Insert new entry
            cursor.execute("""
                INSERT INTO event_series_player_stats (
                    series_id, player_id, series_maps, 
                    series_kills, series_deaths, series_assists, series_fk, series_fd,
                    series_clutches, series_aces, avg_adr_per_series, series_points
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING player_series_stats_id
            """, (series_id, player_id, series_maps, series_kills, series_deaths, series_assists,
                  series_fk, series_fd, series_clutches, series_aces, avg_adr_per_series, series_points))

            # ✅ Fetch the newly inserted `player_series_stats_id`
            new_id = cursor.fetchone()[0]
            print(f"   ✅ Inserted stats for Series {series_id}, Player {player_id} (ID: {new_id})")

    # ✅ Update Adjusted Points AFTER inserting/updating stats
    update_adjusted_points(conn)

    conn.commit()
    print("✅ Aggregated player stats successfully into `event_series_player_stats` table.")

def update_adjusted_points(conn):
    """
    Updates the adjusted_points column in series_player_stats based on:
    - 1 map or unfinished 2-map series (e.g. 1–1): adjusted_points = series_points
    - 2 maps and completed (2–0 or 0–2): adjusted_points = series_points + (28 +/- round diff)
    - 3 maps: adjusted_points = series_points
    - BO5: completed (1 team has 3 wins) adjusted_points = series_points
    """
    cursor = conn.cursor()

    # Case 1: 1 map OR 2 maps but tied (1–1) → no adjustment
    cursor.execute("""
        UPDATE event_series_player_stats
        SET adjusted_points = series_points
        WHERE series_id IN (
            SELECT s.series_id
            FROM event_series s
            JOIN (
                SELECT g.series_id,
                       SUM(CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END) AS home_wins,
                       SUM(CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END) AS away_wins
                FROM event_games g
                GROUP BY g.series_id
            ) win_counts ON s.series_id = win_counts.series_id
            WHERE s.num_maps = 1
               OR (s.num_maps = 2 AND win_counts.home_wins = 1 AND win_counts.away_wins = 1)
        )
    """)

    # Case 2: 3 maps → no adjustment
    cursor.execute("""
        UPDATE event_series_player_stats
        SET adjusted_points = series_points
        WHERE series_id IN (
            SELECT series_id FROM event_series WHERE num_maps = 3
        )
    """)

    # Case 3: 2 maps and series completed → apply 28 +/- round diff
    cursor.execute("""
        UPDATE event_series_player_stats sps
        SET adjusted_points = sps.series_points + COALESCE(adjustment.adjusted_bonus, 0)
        FROM (
            SELECT 
                s.series_id,
                p.player_id,
                CASE 
                    WHEN p.team_id = s.home_team_id THEN 28 + s.home_round_difference
                    WHEN p.team_id = s.away_team_id THEN 28 + s.away_round_difference
                    ELSE 28
                END AS adjusted_bonus
            FROM event_series s
            JOIN (
                SELECT g.series_id,
                       SUM(CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END) AS home_wins,
                       SUM(CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END) AS away_wins
                FROM event_games g
                GROUP BY g.series_id
            ) win_counts ON s.series_id = win_counts.series_id
            JOIN event_player p ON p.team_id IN (s.home_team_id, s.away_team_id)
            WHERE s.num_maps = 2 AND (win_counts.home_wins = 2 OR win_counts.away_wins = 2)
        ) AS adjustment
        WHERE sps.series_id = adjustment.series_id
        AND sps.player_id = adjustment.player_id
    """)

    # Case 4: BO5 completed (one team has 3 wins) → no adjustment
    cursor.execute("""
        UPDATE event_series_player_stats
        SET adjusted_points = series_points
        WHERE series_id IN (
            SELECT s.series_id
            FROM event_series s
            JOIN (
                SELECT g.series_id,
                       SUM(CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END) AS home_wins,
                       SUM(CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END) AS away_wins
                FROM event_games g
                GROUP BY g.series_id
            ) win_counts ON s.series_id = win_counts.series_id
            WHERE s.num_maps >= 3 AND (win_counts.home_wins = 3 OR win_counts.away_wins = 3)
        )
    """)


    conn.commit()
    print("✅ Adjusted points updated successfully.")

# ------------------------- SCRAPE EXECUTION ------------------------- #

def run_full_scrape(url_list, game_id, event_slug, conn):
    """
    Runs the full scraping process for match scores and player stats **sequentially**.
    - Extracts match scores for one match at a time.
    - Immediately scrapes player stats for that match.
    - Inserts player stats into the database before moving to the next match.
    - Updates `game_id` dynamically.

    Args:
        url_list (list): List of match URLs to process.
        game_id (int): The starting game_id for new games.
        conn: The database connection object.

    Returns:
        int: The updated game_id after processing matches.
    """

    print(f"\n🌍 Processing {len(url_list)} Matches")

    filtered_urls = filter_urls_by_latest_scrape(url_list, region=None)

    if filtered_urls:
        cursor = conn.cursor()

        for match_url in filtered_urls:
            print(f"\n🔍 Processing Match: {match_url}")

            # Step 1: Extract match scores
            extract_scores([match_url], event_slug, region=None)

            # Step 2: Get series_id
            match_id = extract_match_id(match_url)
            cursor.execute("SELECT series_id FROM event_series WHERE match_id = %s", (match_id,))
            existing_series = cursor.fetchone()

            if not existing_series:
                print(f"⚠️ Skipping player stats scraping for {match_url} because the series was not inserted.")
                continue

            series_id = existing_series[0]

            # Step 3: Get first game_id for this series
            cursor.execute("SELECT MIN(game_id) FROM event_games WHERE series_id = %s", (series_id,))
            first_game_id = cursor.fetchone()[0]

            if not first_game_id:
                print(f"⚠️ No games found for series {series_id}. Skipping player stats.")
                continue

            print(f"🔍 Scraping player stats starting from game_id {first_game_id} for Series {series_id}.")

            # Step 4: Scrape player stats
            match_df, _ = scrape_and_process_match_stats(match_url, team_names, first_game_id)

            # Step 5: Insert player stats
            if not match_df.empty:
                print("\n📝 Scraped Player Stats Data (Before Database Insertion):")
                insert_player_stats(match_df, conn)
                aggregate_series_player_stats(conn)
            else:
                print("\n⚠️ No valid player stats found. Skipping database insertion.")

        print("\n✅ Full scrape process completed.")
        print("-----------------------------------------------------------------------")

    return game_id

# ------------------------- MAIN EXECUTION ------------------------- #

if __name__ == "__main__":
    logger.info("🚀 Event scraper started (no region)..." + traceback.format_exc())

    # ✅ Setup DB connection
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode=ssl_mode)
        cursor = conn.cursor()
        logger.info("✅ Connected to PostgreSQL" + traceback.format_exc())

        # 🚨 Set the event before running!
        event_slug = 'valorant-champions-2025'

        # 🚨 Set list of urls before running!
        url_list = [
            "https://www.vlr.gg/542278/drx-vs-paper-rex-valorant-champions-2025-lr3"
        ]

        # ✅ Get latest game_id
        latest_game_id = get_latest_game_id(conn)
        game_id = latest_game_id + 1

        # ✅ Run scraper (no region used)
        run_full_scrape(url_list, game_id, event_slug, conn)

    except Exception as e:
        logger.error(f"❌ Error in event scraper: {e}" + traceback.format_exc())

    finally:
        if conn:
            cursor.close()
            conn.close()
            logger.info("🔒 Connection closed" + traceback.format_exc())
