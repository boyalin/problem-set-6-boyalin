import altair as alt
import pandas as pd
import json
import requests
from shiny import App, ui, render
from shinywidgets import output_widget, render_altair

collapsed_data = pd.read_csv(
    '/Users/boyalin/Documents/GitHub/ppha30538_ps/problem-set-6-boyalin/top_alerts_map_byhour/top_alerts_map_byhour.csv')

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)
file_path = "chicago_neighborhoods.geojson"

with open(file_path, 'wb') as file:
    file.write(response.content)
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson['features'])

# define function to get the top alerts based on selected type, subtype, and hour
def filter_data(type, subtype, hour):
    filtered_data = collapsed_data[
        (collapsed_data['updated_type'] == type) &
        (collapsed_data['updated_subtype'] == subtype) &
        (collapsed_data['hour'] == hour)
    ]
    top_10_byhour = filtered_data.sort_values(
        'alert_count', ascending=False).head(10)
    return top_10_byhour

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
    ui.panel_title('Top Location by Alert Type and Hour Dashboard'),
    ui.input_select(
        'alert_type_subtype',
        'Select Alert Type and Subtype:',
        choices=dropdown_choices,
        selected=dropdown_choices[0]),
    # slider for selecting the hour
    ui.input_slider('hour', 'Select Hour:', min=0, max=23, value=3, step=1,
                    animate=True, ticks=True),
    output_widget('top_alerts_plot')
)

# server logic
def server(input, output, session):
    @output()
    @render_altair
    def top_alerts_plot():
        # parse user selection
        # get the selected type and subtype
        selected_type, selected_subtype = input.alert_type_subtype().split(" - ")
        # get the selected hour
        specific_hour = f'{input.hour():02}:00'
        # filter the data based on user input
        filtered_data = filter_data(
            selected_type, selected_subtype, specific_hour)

        lat_domain = [filtered_data['latitude_binned'].min(
        ) - 0.02, filtered_data['latitude_binned'].max() + 0.02]
        long_domain = [filtered_data['longitude_binned'].min(
        ) - 0.02, filtered_data['longitude_binned'].max() + 0.02]

        scatter_plot_by_hour = alt.Chart(filtered_data).mark_circle().encode(
            x=alt.X('latitude_binned:Q', scale=alt.Scale(domain=lat_domain)),
            y=alt.Y('longitude_binned:Q', scale=alt.Scale(domain=long_domain)),
            size=alt.Size('alert_count:Q', scale=alt.Scale(
                domain=[filtered_data['alert_count'].min(
                ), filtered_data['alert_count'].max()],
                range=[120, 350])),
            color=alt.Color('alert_count:Q', scale=alt.Scale(
                domain=[filtered_data['alert_count'].min(
                ), filtered_data['alert_count'].max()],
                range=['skyblue', 'darkblue'])),
            tooltip=['latitude_binned', 'longitude_binned', 'alert_count']
        ).properties(
            title=f"Top 10 {selected_type} - {selected_subtype} Alerts at {specific_hour}",
            width=600, height=600
        )

        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0, stroke='black'
        ).project(type='equirectangular').properties(
            width=600, height=600
        )

        combined_plot_by_hour = map_layer + scatter_plot_by_hour
        return combined_plot_by_hour

app = App(app_ui, server)

# ChatGPT reference for "make a ui.input_slider for 24 hours"
# ChatGDP reference for "parsing hour input as 01:00 format"
