import altair as alt
import pandas as pd
import json
import requests
from shiny import App, ui, render
from shinywidgets import output_widget, render_altair

top_alerts_map = pd.read_csv(
    '/Users/boyalin/Documents/GitHub/ppha30538_ps/problem-set-6-boyalin/top_alerts_map/top_alerts_map.csv')

url = 'https://data.cityofchicago.org/api/geospatial/igwz-8jzy?method=export&format=GeoJSON'
response = requests.get(url)
file_path = 'chicago_neighborhoods.geojson'

with open(file_path, 'wb') as file:
    file.write(response.content)
with open(file_path) as f:
    chicago_geojson = json.load(f)

geo_data = alt.Data(values=chicago_geojson['features'])

# define function to get the top alerts based on selected type and subtype
def get_top_alerts(selected_type, selected_subtype):
    # filter based on type and subtype
    filtered_df = top_alerts_map[(top_alerts_map['updated_type'] == selected_type) & (
        top_alerts_map['updated_subtype'] == selected_subtype)]
    # sort by the highest alert count and return the top 10
    top_alerts = filtered_df.sort_values(
        'alert_count', ascending=False).head(10)
    return top_alerts

# dropdown choices with unique combinations of alert type and subtype
dropdown_choices = (
    top_alerts_map[['updated_type', 'updated_subtype']]
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
        'Select Alert Type and Subtype',
        choices=dropdown_choices,
        selected=dropdown_choices[0]
    ),
    output_widget('top_alerts_plot')
)

# server logic
def server(input, output, session):
    @output
    @render_altair
    def top_alerts_plot():
        # parse user selection
        selected_type, selected_subtype = input.alert_type_subtype().split(" - ")
        top_alerts = get_top_alerts(selected_type, selected_subtype)

        # set the domain for latitude and longitude based on the data
        lat_domain = [top_alerts['latitude_binned'].min(
        ) - 0.02, top_alerts['latitude_binned'].max() + 0.02]
        long_domain = [top_alerts['longitude_binned'].min(
        ) - 0.02, top_alerts['longitude_binned'].max() + 0.02]

        # scatter plot for top alerts
        scatter_plot = alt.Chart(top_alerts).mark_circle().encode(
            x=alt.X('latitude_binned:Q', title='Latitude',
                    scale=alt.Scale(domain=lat_domain)),
            y=alt.Y('longitude_binned:Q', title='Longitude',
                    scale=alt.Scale(domain=long_domain)),
            size=alt.Size('alert_count:Q', title='Number of Alerts'),
            color=alt.Color('alert_count:Q', scale=alt.Scale(
                range=['skyblue', 'darkblue'])),
            tooltip=['latitude_binned', 'longitude_binned', 'alert_count']
        ).properties(
            title=f'Top 10 Locations for {selected_type} - {selected_subtype} Alerts', width=600, height=600
        )

        map_layer = alt.Chart(geo_data).mark_geoshape(
            fillOpacity=0, stroke='black'
        ).project(type = 'equirectangular').properties(
            width=600, height=600
        )
        
        combined_plot = map_layer + scatter_plot
        return combined_plot

app = App(app_ui, server)

# ChatGPT reference for "make a dropdown choices with unique combinations of alert type and subtype" and "parse the combination when plotting using Altair"
