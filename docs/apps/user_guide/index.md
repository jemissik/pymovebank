# User guide

```{tip}
Want a downloadable version of the docs? This documentation is also [available for download](https://readthedocs.org/projects/ecodata-apps/downloads/) as a PDF, Epub, or zipped HTML.
```

## Getting started

ECODATA-Prepare is a set of four Python-based apps to read, process, and create animations from animal tracking data and gridded environmental data. [Read here](../index) for an overview and to learn how to install, contribute and get support. Before using this program, gather files you want to use with the app: this could include 
* a .csv file of tracking data, in Movebank’s .csv format
* NetCDF files of environmental data (you can [order these](https://ecodata-apps.readthedocs.io/en/latest/environmental_data.html) from NASA or ECMWF)
* shapefiles
* a folder of sequentially-numbered .png files that are frames for an animation (you can create these with [ECODATA-Animate](https://ecodata-animate.readthedocs.io/en/latest/))

If needed, see the [installation instructions](../installation) to install or update the program. 

See [below](#opening-ecodata-prepare) for instructions to open the program. When it opens, it will display the main panel, showing the four apps. Click on an app to launch it. From there, you can navigate between apps within the interface, or switch between them by pasting these URLs in your browser window:

* Main app gallery: <http://localhost:5006>
* Tracks Explorer App: <http://localhost:5006/tracks_explorer_app>
* Gridded Data Explorer App: <http://localhost:5006/gridded_data_explorer_app>
* Subsetter App: <http://localhost:5006/subsetter_app>
* Movie Maker App: <http://localhost:5006/movie_maker_app>

![ecodata-prepare_panel](../images/ecodata-prepare_panel.png)

## Opening ECODATA-Prepare

There are a few ways you can launch the apps.

### 1. Use the launch file

The easiest way is to double-click on the launch file (``ecodata.command`` for Mac,
``ecodata.bat`` for Windows). A terminal window will open, indicating that the apps are launching. When the apps finish launching, a window will open on your default web browser, showing the app gallery. The apps are running locally at localhost:5006. *Note: There may be a short wait (10+ seconds) before the browser window opens.*

You may receive a message "Do you want the application "python3.9" to accept incoming network connections?" You can click Allow.

Keep the terminal application you used to launch the program open while running the app. To shut down the apps, close the terminal that you used for launching.

### 2. Launch from the terminal

Launch the ECODATA-Prepare apps using the command below. For **Mac/Linux**, you will run the command below from the built-in Mac “Terminal” application, or any other terminal app. For **Windows**, you will run the command using the Miniforge Prompt. If this is not already open, find it by searching for "Miniforge Prompt" in the start menu.

```bash
mamba activate eco
python -m ecodata.app
```

A window will open on your default web browser, showing the main app gallery page (the apps are running locally at ``localhost:5006``). There may be a short wait the first time you launch the apps, or the first time you launch after an update.

You may receive a message "Do you want the application "python3.9" to accept incoming network connections?" You can click Allow.

Keep the terminal application you used to launch the program open while running the app. To shut down the apps, close the terminal that you used for launching.

### 3. Launch using Anaconda

If you have [installed Anadonda](https://ecodata-apps.readthedocs.io/en/latest/installation.html#install-using-anaconda-alternative-method) (Anaconda PowerShell for Windows, Anaconda Navigator for Mac), you can also launch ECODATA-Prepare through this program.

To launch in Windows,

- Open Anaconda PowerShell.
- Copy-paste the below code into the prompt window, and press Enter:

```bash
conda activate eco
python -m ecodata.app
```

To launch on Mac,

- Open Anaconda Navigator.
- Select Environments from the upper left and navigate to "ecodata".

![anaconda_navigator](./images/anaconda_navigator.png)

- Hit the play button and select "Open Terminal".
- A Terminal window will open. Enter the following and hit Return:

```bash
python -m ecodata.app
```

## Apps
```{toctree}
---
maxdepth: 2
---
tracks_explorer
gridded_data_explorer
subsetter
movie_maker

```