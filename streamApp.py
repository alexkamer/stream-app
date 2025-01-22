import pandas as pd
import httpx
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime, timedelta
import streamlit as st

st.set_page_config(layout="wide")

# URLs to scrape
all_box_urls = {
    'Football': "https://nflbox.me/football-streams",
    'Basketball': "https://www.nbabox.me/watch-baketball-online",
    'Baseball': "https://mlbbox.me/baseball-streams",
    "Hockey": "https://nhlbox.me/hockey-streams",
    "UFC": "https://mmastreams.me/ufc-streams",
    "Racing": "https://f1box.me/motor-racing-streams",
    "Golf": "https://golfstreams.me/live-golf-streams"
}
# all_box_urls = {
#     "UFC": "https://mmastreams.me/ufc-streams"
# }

async def fetch_and_parse(client, box_name, url):
    """Fetch and parse the webpage."""
    response = await client.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    a_tags = soup.find_all('a')
    # Filter tags with "aria-controls" in them
    filtered_a_tags = [str(tag) for tag in a_tags if "aria-controls" in str(tag)]
    return box_name, filtered_a_tags

async def fetch_all_box_a_tags():
    """Main asynchronous function to fetch all URLs."""
    all_box_a_tags = {}
    async with httpx.AsyncClient() as client:
        # Create tasks for fetching all URLs
        tasks = [fetch_and_parse(client, name, url) for name, url in all_box_urls.items()]
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        # Populate the results into the dictionary
        for box_name, a_tags in results:
            all_box_a_tags[box_name] = a_tags
    return all_box_a_tags

@st.cache_data(show_spinner=True)
def get_cached_dataframe():
    """Fetch, parse, and cache the DataFrame."""
    all_box_a_tags = asyncio.run(fetch_all_box_a_tags())
    allBox_df = []

    for sport in all_box_a_tags:
        for tag in all_box_a_tags[sport]:
            game_name = tag.split('title="')[1].split('"')[0]
            href = tag.split('href="/')[1].split('"')[0]
            # href = f"{href.split('/')[1]}/{href.split('/')[0]}"
            href = f"{min(href.split('/'), key=len)}/{max(href.split('/'), key=len)}"

            try:
                start_date = tag.split('content="')[1].split('"')[0]
                # Parse the string into a datetime object
                start_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
                # Subtract 6 hours
                start_date = start_date - timedelta(hours=6)
                # Convert back to string if needed
                start_date = start_date.strftime("%Y-%m-%dT%H:%M")
            except Exception as e:
                start_date = None
            allBox_df.append({
                'sport': sport,
                "game_name": game_name,
                'href': href,
                'start_date': start_date
            })

    allBox_df = pd.DataFrame(allBox_df)
    return allBox_df.sort_values(by='start_date', na_position='first')

# Fetch the cached DataFrame
allBox_df = get_cached_dataframe()

def format_start_date(row):
    if row["start_date"] is None:
        return "Live Television"
    return row["start_date"]
def extract_date_and_time_with_label(start_date):
    if start_date is None:
        return None, "Live Television"
    else:
        dt = datetime.fromisoformat(start_date)
        date = dt.strftime("%Y-%m-%d")  # Extract only the date
        time = dt.strftime("%I:%M %p")  # 12-hour format with AM/PM
        
        # Calculate relative day (Today, Tomorrow, etc.)
        today = datetime.now().date()
        game_date = dt.date()
        if game_date == today:
            day_label = "Today"
        elif game_date == today + timedelta(days=1):
            day_label = "Tomorrow"
        else:
            day_label = game_date.strftime("%A")  # Day of the week
        
        return date, f"{time} ({day_label})"

# Apply function to split start_date and add labels
allBox_df[["start_date", "start_time"]] = allBox_df["start_date"].apply(
    lambda x: pd.Series(extract_date_and_time_with_label(x))
)
allBox_df["display_date"] = allBox_df.apply(format_start_date, axis=1)
selected_sport = st.selectbox(
    "Select a sport:",
    allBox_df["sport"].unique()
)

# Filter DataFrame based on selected sport
filtered_df = allBox_df[allBox_df["sport"] == selected_sport]

# Display expanders for each show
for _, row in filtered_df.iterrows():
    expander = st.expander(f"{row['game_name']} ({row['start_time']})")
    with expander:
        st.write(f"**Sport:** {row['sport']}")
        st.write(f"**Game Name:** {row['game_name']}")
        st.write(f"**Date:** {row['start_date'] or 'Live Television'}")
        st.write(f"**Time:** {row['start_time']}")
# Streamlit App
st.title("Game Picker")

st.dataframe(allBox_df)











# Initialize session state for selected games
if "selected_games" not in st.session_state:
    st.session_state["selected_games"] = []

addGameClicked = False

with st.sidebar:
    sport_names = sorted(list(allBox_df['sport'].unique()))
    selected_sport = st.selectbox(options=sport_names, label="Select a Sport", index=0)
    selected_sport_df = allBox_df[allBox_df['sport'] == selected_sport]
    game_choices = list(selected_sport_df['game_name'].unique())
    # selected_game = st.selectbox(options=game_choices, label="Select the Game")
    games_selected_within_choices = [x for x in game_choices if x in st.session_state["selected_games"]]
    selected_game = st.multiselect(options=game_choices, label="Select the Game" , default=games_selected_within_choices)
    if st.button("Add Game"):
        # row_selected = allBox_df[(allBox_df['sport'] == selected_sport) & (allBox_df['game_name'] == selected_game)]
        row_selected = allBox_df[(allBox_df['sport'] == selected_sport) & (allBox_df['game_name'].isin(selected_game))]
        # Add the selected game to session state
        # st.session_state["selected_games"].append(row_selected.iloc[0].to_dict())
        st.session_state["selected_games"].extend(row_selected['href'].to_list())
        st.session_state["selected_games"] = list(set(st.session_state["selected_games"]))
        addGameClicked = True

    # Add a button to clear the cache
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.rerun()
        st.success("Cache has been cleared!")

def create_iframe_html(urls):
    iframe_html = f"""
        <style>
            .stApp {{
                background-color: black;
            }}
            .grid-container {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(45%, 1fr));
                gap: 10px;
                width: 100%;
            }}
            .iframe-container {{
                position: relative;
                width: 100%;
                padding-bottom: 56.25%; /* 16:9 aspect ratio */
                height: 0;
                overflow: hidden;
            }}
            .iframe-container iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                border: 0;
            }}
        </style>
        <div class="grid-container">
        """

    for url in urls:
        iframe_html += f"""
        <div class="iframe-container">
            <iframe src='{url}' 
                    scrolling='no' 
                    allowfullscreen 
                    allowtransparency 
                    referrerpolicy='unsafe-url'>
            </iframe>
        </div>
        """

    iframe_html += "</div>"
    return iframe_html

# Display all selected games
if st.session_state["selected_games"]:
    urls = [f"https://embedsports.me/{game}-1" for game in st.session_state["selected_games"]]
    temp_html = create_iframe_html(urls)
    st.markdown(temp_html, unsafe_allow_html=True)
    # st.write(urls)

    # Add an option to clear all selected games
    if st.button("Clear Selected Games"):
        st.session_state["selected_games"] = []
        st.rerun()



