from pathlib import Path
import geopandas as gpd
import hvplot.pandas  # noqa
import hvplot.xarray  # noqa
import panel as pn
import param

import ecodata as eco
from ecodata.app.models import PMVCard, FileSelector
from ecodata.panel_utils import param_widget, register_view, try_catch, rename_param_widgets
from ecodata.plotting import map_tile_options, plot_tracks_with_tiles
from ecodata.app.config import DEFAULT_TEMPLATE

# from panel_jstree.widgets.jstree import FileTree


class TracksExplorer(param.Parameterized):
    load_tracks_button = param_widget(pn.widgets.Button(button_type="primary", name="Load data"))
    tracksfile = param_widget(FileSelector(expanded=None))

    # filetree = param_widget(FileTree("/Users/jmissik/Desktop/repos.nosync/ecodata/ecodata/datasets/user_datasets",
    # select_multiple=False))
    # file_selector = param_widget(FileSelector("~", root_directory="/"))

    tracks = param.ClassSelector(class_=gpd.GeoDataFrame, precedence=-1)
    tracks_extent = param.ClassSelector(class_=gpd.GeoDataFrame, precedence=-1)
    tracks_boundary_shape = param_widget(
        pn.widgets.Select(
            options={"Rectangular": "rectangular", "Convex hull": "convex_hull"},
            value="rectangular",
            name="Boundary shape,",
        )
    )
    tracks_buffer = param_widget(
        pn.widgets.EditableFloatSlider(name="Buffer size", start=0.01, end=1, step=0.01, value=0.1)
    )
    boundary_update = param_widget(pn.widgets.Button(button_type="primary", value=False, name="Update boundary"))

    # output_file_button = param_widget(pn.widgets.Button(button_type='primary', name='Choose output file'))
    output_fname = param_widget(
        pn.widgets.TextInput(
            placeholder="Select a file...",
            value=str(
                (Path.home() / "Downloads/tracks_extent.geojson").resolve()
                if (Path.home() / "Downloads").exists()
                else (Path.home() / "tracks_extent.geojson").resolve()
            ),
            name="Output file",
        )
    )
    save_tracks_extent_button = param_widget(pn.widgets.Button(name="Save extent", button_type="primary"))

    ds_checkbox = param_widget(
        pn.widgets.Checkbox(
            name="Datashade tracks",
            value=True,
        )
    )
    map_tile = param_widget(pn.widgets.Select(options=map_tile_options, value="EsriWorldStreetMap", name="Map tile"))

    plot_pane = param.ClassSelector(
        class_=pn.pane.HoloViews,
        default=pn.pane.HoloViews(
            None,
            sizing_mode="stretch_both",
        ),
    )
    view = param.ClassSelector(class_=pn.Column, default=pn.Column(sizing_mode="stretch_both"))

    status_text = param.String("Ready...")

    def __init__(self, **params):
        # params["plot_pane"] = pn.pane.HoloViews(
        #     None, sizing_mode="stretch_both",
        # )
        # params["view"] = pn.Column(sizing_mode="stretch_both")
        super().__init__(**params)

        # Reset names for panel widgets
        rename_param_widgets(
            self,
            [
                "load_tracks_button",
                "tracksfile",
                "output_fname",
                "save_tracks_extent_button",
                "tracks_boundary_shape",
                "boundary_update",
                "tracks_buffer",
                "ds_checkbox",
                "map_tile",
            ]
        )

        self.file_card = PMVCard(
            self.tracksfile,
            # self.file_selector,
            self.load_tracks_button,
            title="Input Data",
        )

        self.options_col = pn.Column(
            self.tracks_boundary_shape,
            self.tracks_buffer,
            self.boundary_update,
        )

        self.widgets = pn.Column(
            self.file_card,
            self.output_fname,
            self.save_tracks_extent_button,
            sizing_mode="stretch_height"
        )

        self.alert = pn.pane.Markdown(self.status_text)

        # # Add view
        # self.view = pn.Column(
        #         pn.Column(pn.pane.Markdown("## Select file to plot!")),
        #         self.widgets,
        #         pn.pane.Alert(self.status_text),
        #         sizing_mode="stretch_both")
        # Add view
        # self.view[:] = [
        #     pn.Row(self.plot_pane),
        #     self.widgets,
        #     self.alert,
        # ]

    @try_catch()
    @param.depends("load_tracks_button.value", watch=True)  # depends on load_tracks_button
    def load_data(self):
        if self.tracksfile.value:
            # if self.file_selector.value:
            self.status_text = "Loading data..."
            val = self.tracksfile.value  # or self.filetree.value[0]
            # val = self.file_selector.value[0]
            self.tracksfile.expanded = False
            tracks = eco.read_track_data(val)
            self.status_text = "Track file loaded"
            self.tracks_extent = eco.get_tracks_extent(
                tracks, boundary_shape=self.tracks_boundary_shape.value, buffer=self.tracks_buffer.value
            )
            self.tracks = tracks

        else:
            self.status_text = "File path must be selected first!"

    # @param.depends("filetree.value", watch=True)
    # def update_tf_on_ft(self):
    #     if self.filetree.value:
    #         self.tracksfile.value = self.filetree.value[-1]
    #     else:
    #         self.tracksfile.value = ""
    #
    # @param.depends("tracksfile.value", watch=True)
    # def update_ft_on_tf(self):
    #     if self.tracksfile.value:
    #         self.filetree.value = [self.tracksfile.value]
    #     else:
    #         self.filetree.value = []

    @try_catch()
    @param.depends("boundary_update.value", watch=True)
    def update_tracks_extent(self):
        self.tracks_extent = eco.get_tracks_extent(
            self.tracks, boundary_shape=self.tracks_boundary_shape.value, buffer=self.tracks_buffer.value
        )

    # @param.depends("output_file_button.value", watch=True)
    # def get_output_fname(self):
    #     downloads_dir = (Path.home() / "Downloads")
    #     if downloads_dir.exists():
    #         default_dir = downloads_dir
    #     else:
    #         default_dir = Path.cwd()
    #     filename = select_output(initial_dir=default_dir, initial_file='tracks_extent.geojson', extension='.geojson')
    #     self.output_fname.value = filename

    @try_catch()
    @param.depends("save_tracks_extent_button.value", watch=True)
    def save_tracks_extent(self):
        outfile = Path(self.output_fname.value).resolve()
        # TODO check that tracks/extent exists
        if self.tracks_extent is not None:
            self.tracks_extent.to_file(outfile, driver="GeoJSON")
            self.status_text = f"File saved to: {outfile}"
        else:
            self.status_text = "Tracks data must be added before a tracks extent file can be saved!"

    @try_catch()
    @param.depends("status_text", watch=True)
    def update_status_view(self):
        self.alert.object = self.status_text

    @try_catch()
    @param.depends("tracks", "boundary_update.value", "ds_checkbox.value", "map_tile.value", watch=True)
    def update_view(self):
        self.status_text = "Creating plot..."

        plot = (
            plot_tracks_with_tiles(
                self.tracks,
                tiles=self.map_tile.value,
                datashade=self.ds_checkbox.value,
                cmap="fire",
                c="r",
                marker="circle",
                alpha=0.3,
            ).opts(
                responsive=True,
            )
            * self.tracks_extent.hvplot(fill_color=None, line_color="r", geo=True, project=True).opts(
                responsive=True,
            )
        ).opts(
            # responsive=True,
            # sizing_mode="stretch_both",
            frame_height=800,
            frame_width=600,
            active_tools=["wheel_zoom"],
        )
        self.options_col[:] = [
            self.tracks_boundary_shape,
            self.tracks_buffer,
            self.boundary_update,
            self.map_tile,
            self.ds_checkbox,
        ]

        # self.options_col.append(self.map_tile)
        # self.options_col.append(self.ds_checkbox)

        self.plot_pane.object = plot

        self.status_text = "Plot created!"


@register_view()
def view():
    viewer = TracksExplorer()
    template = DEFAULT_TEMPLATE(
        sidebar=[viewer.options_col],
        main=[viewer.alert, viewer.plot_pane, viewer.widgets],
        # header=viewer.alert
    )
    return template



if __name__ == "__main__":
    pn.serve({Path(__file__).name: view})

if __name__.startswith("bokeh"):
    view()
