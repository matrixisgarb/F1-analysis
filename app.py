import fastf1
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
import os

os.makedirs('f1_cache', exist_ok=True)
fastf1.Cache.enable_cache('f1_cache')

st.set_page_config(page_title='F1 Lap Time Analysis', layout='wide')
st.title('🏎️ F1 Lap Time Analysis')

st.sidebar.header('Select Race')

year = st.sidebar.selectbox('Season', [2024, 2023, 2022])

race = st.sidebar.selectbox('Race', [
    'Bahrain', 'Saudi Arabia', 'Australia', 'Japan', 'China',
    'Miami', 'Emilia Romagna', 'Monaco', 'Canada', 'Spain',
    'Austria', 'Britain', 'Hungary', 'Belgium', 'Netherlands',
    'Italy', 'Azerbaijan', 'Singapore', 'United States',
    'Mexico', 'Brazil', 'Las Vegas', 'Qatar', 'Abu Dhabi'
])

@st.cache_resource
def load_session(year, race):
    session = fastf1.get_session(year, race, 'R')
    session.load()
    return session

with st.spinner('Loading race data...'):
    session = load_session(year, race)

laps = session.laps[['Driver', 'LapNumber', 'LapTime', 'Compound']].copy()
laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
laps = laps[laps['LapTimeSeconds'] < laps['LapTimeSeconds'].quantile(0.95)]

drivers = sorted(laps['Driver'].unique().tolist())
selected_driver = st.sidebar.selectbox('Highlight Driver', drivers,
                                        index=drivers.index('PIA') if 'PIA' in drivers else 0)
compare_driver = st.sidebar.selectbox('Compare With', ['None'] + drivers, index=0)

def get_pit_laps(driver_code):
    driver_laps = session.laps.pick_drivers(driver_code)
    return driver_laps[driver_laps['PitOutTime'].notna()]

compound_colours = {
    'SOFT': '#e8002d',
    'MEDIUM': '#ffd700',
    'HARD': '#ffffff',
    'INTERMEDIATE': '#39b54a',
    'WET': '#0067ff'
}

fig, ax = plt.subplots(figsize=(18, 8))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')

for driver in laps['Driver'].unique():
    if driver == selected_driver or driver == compare_driver:
        continue
    driver_laps = laps[laps['Driver'] == driver]
    ax.plot(driver_laps['LapNumber'], driver_laps['LapTimeSeconds'],
            color='#444466', linewidth=1, alpha=0.5)

all_drivers = [d for d in laps['Driver'].unique()
               if d != selected_driver and d != compare_driver]
last_laps = []
for driver in all_drivers:
    driver_laps = laps[laps['Driver'] == driver]
    if not driver_laps.empty:
        last_laps.append((driver, driver_laps.iloc[-1]['LapNumber'],
                         driver_laps.iloc[-1]['LapTimeSeconds']))

last_laps.sort(key=lambda x: x[2])
min_spacing = 0.4
prev_y = None
for driver, x, y in last_laps:
    if prev_y is not None and abs(y - prev_y) < min_spacing:
        y = prev_y + min_spacing
    ax.text(x + 0.5, y, driver, fontsize=6, color='#888899', va='center')
    prev_y = y

highlight_laps = laps[laps['Driver'] == selected_driver]
pit_laps = get_pit_laps(selected_driver)

for compound, group in highlight_laps.groupby('Compound'):
    colour = compound_colours.get(compound, '#ff8000')
    ax.plot(group['LapNumber'], group['LapTimeSeconds'],
            color=colour, linewidth=2.5,
            label=f'{selected_driver} ({compound})', zorder=5)

y_min, y_max = ax.get_ylim()
for _, pit_lap in pit_laps.iterrows():
    ax.axvline(x=pit_lap['LapNumber'], color='#ff8000',
               linestyle='--', alpha=0.4, linewidth=1)
    ax.text(pit_lap['LapNumber'] + 0.3, y_min + (y_max - y_min) * 0.02,
            'PIT', fontsize=7, color='#ff8000', alpha=0.9)

compare_laps = None
if compare_driver != 'None' and compare_driver != selected_driver:
    compare_laps = laps[laps['Driver'] == compare_driver]
    compare_pit_laps = get_pit_laps(compare_driver)

    for compound, group in compare_laps.groupby('Compound'):
        colour = compound_colours.get(compound, '#00bfff')
        ax.plot(group['LapNumber'], group['LapTimeSeconds'],
                color=colour, linewidth=2.5, linestyle='--',
                label=f'{compare_driver} ({compound})', zorder=5)

    for _, pit_lap in compare_pit_laps.iterrows():
        ax.axvline(x=pit_lap['LapNumber'], color='#00bfff',
                   linestyle='--', alpha=0.4, linewidth=1)
        ax.text(pit_lap['LapNumber'] + 0.3, y_min + (y_max - y_min) * 0.06,
                'PIT', fontsize=7, color='#00bfff', alpha=0.9)

ax.set_title(f'{year} {race} GP — Lap Times', fontsize=15, color='white', pad=15)
ax.set_xlabel('Lap Number', color='white')
ax.set_ylabel('Lap Time (seconds)', color='white')
ax.tick_params(colors='white')
ax.spines['bottom'].set_color('#444466')
ax.spines['left'].set_color('#444466')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend(facecolor='#1a1a2e', labelcolor='white', fontsize=9)

st.pyplot(fig)

st.subheader('📊 Race Summary')

def driver_stats(driver_code, driver_laps):
    pit_count = len(get_pit_laps(driver_code))
    return {
        'Driver': driver_code,
        'Avg Lap Time (s)': round(driver_laps['LapTimeSeconds'].mean(), 3),
        'Fastest Lap (s)': round(driver_laps['LapTimeSeconds'].min(), 3),
        'Slowest Lap (s)': round(driver_laps['LapTimeSeconds'].max(), 3),
        'Pit Stops': pit_count
    }

stats = [driver_stats(selected_driver, highlight_laps)]
if compare_laps is not None:
    stats.append(driver_stats(compare_driver, compare_laps))

st.dataframe(pd.DataFrame(stats), hide_index=True, use_container_width=True)