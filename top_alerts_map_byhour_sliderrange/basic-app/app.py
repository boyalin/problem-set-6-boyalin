import altair as alt
import pandas as pd
import json
import requests
from shiny import App, ui, render
from shinywidgets import output_widget, render_altair

collapsed_data = pd.read_csv(
    '/Users/boyalin/Documents/GitHub/ppha30538_ps/problem-set-6-boyalin/top_alerts_map_byhour/top_alerts_map_byhour.csv'
)

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)
file_path = 'chicago_neighborhoods.geojson'

with open(file_path, 'wb') as file:
    file.write(response.content)
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson['features'])

# define function to get top alerts for a specific hour input
def filter_data_specific_hour(type, subtype, hour):
    filtered_data = collapsed_data[
        (collapsed_data['updated_type'] == type) &
        (collapsed_data['updated_subtype'] == subtype) &
        (collapsed_data['hour'] == hour)
    ]
    return filtered_data.sort_values('alert_count', ascending=False).head(10)

# define function to get top alerts for a range of hour input
def filter_data_by_range(type, subtype, hour_start, hour_end):
    hour_range = [f'{h:02}:00' for h in range(hour_start, hour_end + 1)]
    filtered_data = collapsed_data[
        (collapsed_data['updated_type'] == type) &
        (collapsed_data['updated_subtype'] == subtype) &
        (collapsed_data['hour'].isin(hour_range))
    ]
    return (
        filtered_data.groupby(['latitude_binned', 'longitude_binned'])
        .agg({'alert_count': 'sum'})
        .reset_index()
        .sort_values('alert_count', ascending=False)
        .head(10)
    )

# dropdown choices with unique combinations of alert type and subtype
dropdown_choices = (
    collapsed_data[['updated_type', 'updated_subtype']]
    .drop_duplicates()
    .sort_values(by=['updated_type', 'updated_subtype'])
    .apply(lambda row: f"{row['updated_type']} - {row['updated_subtype']}", axis=1)
    .tolist()
)

# UI side
app_ui = ui.page_fluid(
    ui.panel_title('Top Location by Alert Type Dashboard'),
    ui.input_select(
        'alert_type_subtype',
        'Select Alert Type and Subtype:',
        choices=dropdown_choices,
        selected=dropdown_choices[0]
    ),
    ui.input_switch('switch_button', 'Toggle to switch to range of hours', value=False),
    # show hour range first
    ui.panel_conditional('!input.switch_button',
                         ui.input_slider(id='hour_range', label='Select Hour Range:', min=0, max=23, value=(6, 9), step=1, animate=True, ticks=True)),
    # switch to specific hour when toggle is true
    ui.panel_conditional('input.switch_button',
                         ui.input_slider(id='single_hour', label='Select Single Hour:', min=0, max=23, value=6, step=1, animate=True, ticks=True)),
    output_widget('top_alerts_plot')
)

# server logic
def server(input, output, session):
    @output
    @render_altair
    def top_alerts_plot():
        # parse user selection
        selected_type, selected_subtype = input.alert_type_subtype().split(' - ')

        # determine the hour range based on toggle
        if input.switch_button():
            # ensure hour is in 2-digit format
            hour = f'{input.single_hour():02}:00'
            filtered_data = filter_data_specific_hour(
                selected_type, selected_subtype, hour)
        else:
            hour_start, hour_end = input.hour_range()
            filtered_data = filter_data_by_range(
                selected_type, selected_subtype, hour_start, hour_end)

        lat_domain = [filtered_data['latitude_binned'].min(
        ) - 0.02, filtered_data['latitude_binned'].max() + 0.02]
        long_domain = [filtered_data['longitude_binned'].min(
        ) - 0.02, filtered_data['longitude_binned'].max() + 0.02]

        scatter_plot = alt.Chart(filtered_data).mark_circle().encode(
            x=alt.X('latitude_binned:Q', scale=alt.Scale(domain=lat_domain)),
            y=alt.Y('longitude_binned:Q', scale=alt.Scale(domain=long_domain)),
            size=alt.Size('alert_count:Q', title='Alert Count', scale=alt.Scale(
                domain=[filtered_data['alert_count'].min(), filtered_data['alert_count'].max()], range=[120, 350])),
            color=alt.Color('alert_count:Q', scale=alt.Scale(
                range=['skyblue', 'darkblue']), title='Alert Count'),
            tooltip=['latitude_binned', 'longitude_binned', 'alert_count']
        ).properties(
            title=f'Top 10 {selected_type} - {selected_subtype} Alerts',
            width=600, height=600
        )

        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0, stroke='black'
        ).project(type='equirectangular').properties(
            width=600, height=600
        )

        combined_plot = map_layer + scatter_plot
        return combined_plot

app = App(app_ui, server)

# ChatGDP reference for "use ui.input_switch to switch between hour range and specific hour and return corresponding chart"
