import logging
from pathlib import Path

import hvplot.pandas  # noqa
import hvplot.xarray  # noqa
import panel as pn
import param
from panel.io.loading import start_loading_spinner, stop_loading_spinner

import ecodata as eco
from ecodata.app.models import FileSelector
from ecodata.panel_utils import param_widget, register_view, try_catch, rename_param_widgets
from ecodata.app.config import DEFAULT_TEMPLATE

logger = logging.getLogger(__file__)


class Subsetter(param.Parameterized):

    # Input GIS file
    input_file = param_widget(FileSelector(constrain_path=False, expanded=True))

    # Widgets common to all selection options
    buffer = param_widget(
        pn.widgets.EditableFloatSlider(name="Buffer size", start=0, end=1, step=0.01, value=0, sizing_mode="fixed")
    )
    clip = param_widget(pn.widgets.Checkbox(name="Clip features", value=True, align="end"))
    output_file = param_widget(
        pn.widgets.TextInput(
            placeholder="Choose an output file...",
            value=str(
                (Path.home() / "Downloads/subset.shp").resolve()
                if (Path.home() / "Downloads").exists()
                else (Path.home() / "subset.shp").resolve()
            ),
            name="Output file",
        )
    )

    # Subset type options
    option_picker = param_widget(
        pn.widgets.RadioButtonGroup(
            name="Subsetting options",
            options={"Bounding Box": "bbox", "Track Points": "track_points", "Bounding Geometry": "bounding_geom"},
        )
    )

    # bbox options
    bbox_latmin = param_widget(
        pn.widgets.FloatInput(name="Lat min", value=0, step=1e-2, start=-90, end=90, sizing_mode="fixed")
    )
    bbox_latmax = param_widget(
        pn.widgets.FloatInput(name="Lat max", value=0, step=1e-2, start=-90, end=90, sizing_mode="fixed")
    )
    bbox_lonmin = param_widget(
        pn.widgets.FloatInput(name="Lon min", value=0, step=1e-2, start=-180, end=180, sizing_mode="fixed")
    )
    bbox_lonmax = param_widget(
        pn.widgets.FloatInput(name="Lon max", value=0, step=1e-2, start=-180, end=180, sizing_mode="fixed")
    )

    # Track file options
    tracks_file = param_widget(FileSelector(constrain_path=False, expanded=True))
    boundary_type_tracks = param_widget(
        pn.widgets.RadioBoxGroup(
            name="Boundary type", options={"Rectangular": "rectangular", "Convex hull": "convex_hull"}
        )
    )

    # Bounding geom options
    bounding_geom_file = param_widget(FileSelector(constrain_path=False, expanded=True))

    boundary_type_geom = param_widget(
        pn.widgets.RadioBoxGroup(
            name="Boundary type", options={"Rectangular": "rectangular", "Convex hull": "convex_hull", "Exact": "mask"}
        )
    )
    show_plot = param_widget(pn.widgets.Checkbox(name="Show plot", value=True, align="end"))

    # Go button
    create_subset_button = param_widget(
        pn.widgets.Button(name="Create subset", button_type="primary", sizing_mode="fixed")
    )

    # Status
    status_text = param.String("Ready...")

    def __init__(self, **params):
        super().__init__(**params)


        # Reset names for panel widgets
        rename_param_widgets(
            self,
            [
                "input_file",
                "buffer",
                "clip",
                "output_file",
                "bbox_latmin",
                "bbox_latmax",
                "bbox_lonmin",
                "bbox_lonmax",
                "tracks_file",
                "boundary_type_tracks",
                "bounding_geom_file",
                "boundary_type_geom",
                "show_plot",
                "create_subset_button",
            ]
        )

        # Widget groups
        self.bbox_widgets = pn.Column(
            pn.Row(self.bbox_latmin, self.bbox_latmax), pn.Row(self.bbox_lonmin, self.bbox_lonmax)
        )

        self.track_points_widgets = pn.Column(self.tracks_file, self.boundary_type_tracks, self.buffer)

        self.bounding_geom_widgets = pn.Column(self.bounding_geom_file, self.boundary_type_geom, self.buffer)

        self.shared_widgets = pn.Column(self.clip, self.output_file, self.show_plot, self.create_subset_button)

        self.option_picker_mapper = {
            "bbox": self.bbox_widgets,
            "track_points": self.track_points_widgets,
            "bounding_geom": self.bounding_geom_widgets,
        }

        self.status = pn.pane.Alert(self.status_text)
        # View
        self.view_objects = {
            "plot": 0,
            "input_file": 1,
            "option_picker": 2,
            "option_widgets": 3,
            "shared_widgets": 4,
            "status": 5,
        }

        self.alert = pn.pane.Markdown(self.status_text)

        self.view = pn.Column(
            pn.pane.Markdown("## Create a subset!"),
            self.input_file,
            self.option_picker,
            self.bbox_widgets,
            self.shared_widgets,
        )

    @try_catch()
    @param.depends("status_text", watch=True)
    def update_status_text(self):
        self.alert.object = self.status_text

    @try_catch()
    @param.depends("option_picker.value", watch=True)
    def _update_widgets(self):
        self.status_text = "updated widgets"
        option = self.option_picker.value
        widgets = self.option_picker_mapper[option]
        self.view[self.view_objects["option_widgets"]] = widgets

    @try_catch()
    def get_args_from_widgets(self):
        args = dict(filename=self.input_file.value, clip=self.clip.value, outfile=self.output_file.value)

        if self.option_picker.value == "bbox":
            args["bbox"] = (
                self.bbox_lonmin.value,
                self.bbox_latmin.value,
                self.bbox_lonmax.value,
                self.bbox_latmax.value,
            )
        elif self.option_picker.value == "track_points":
            args["track_points"] = self.tracks_file.value
            args["boundary_type"] = self.boundary_type_tracks.value
            args["buffer"] = self.buffer.value

        elif self.option_picker.value == "bounding_geom":
            args["bounding_geom"] = self.bounding_geom_file.value
            args["boundary_type"] = self.boundary_type_geom.value
            args["buffer"] = self.buffer.value

        return args

    @try_catch()
    @param.depends("create_subset_button.value", watch=True)
    def create_subset(self):

        self.status_text = "Creating subset..."
        start_loading_spinner(self.view)
        try:
            args = self.get_args_from_widgets()
            subset = eco.subset_data(**args)
            if len(subset["subset"]) == 0:
                self.status_text = "No features in subset"
            else:
                self.status_text = "Subset created!"
                if self.show_plot.value:
                    plot = eco.plot_subset(**subset)
                    self.view[self.view_objects["plot"]] = pn.pane.Matplotlib(plot)
                else:
                    self.view[self.view_objects["plot"]] = pn.pane.Markdown(" ## Subset saved to output directory")
        except Exception as e:
            msg = "Error creating subset. Make sure all necessary inputs are provided."
            logger.warning(msg + f":\n{e!r}")
            self.view[self.view_objects["plot"]] = pn.pane.Markdown("## Create a subset!")
            self.status_text = msg
        finally:
            stop_loading_spinner(self.view)


@register_view()
def view():
    viewer = Subsetter()
    template = DEFAULT_TEMPLATE(
        main=[viewer.alert, viewer.view],
    )
    return template


if __name__ == "__main__":
    pn.serve({Path(__file__).name: view})


if __name__.startswith("bokeh"):
    view()
