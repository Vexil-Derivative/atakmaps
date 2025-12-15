ATAK Map Projects
-----------------

This repo holds various ATAK-related map projects and may drift over time as different data/maps are used. Each project lives in its own folder under `projects/`.

Projects
- MVUM — Motor Vehicle Use Map export to ATAK KML/KMZ (roads/trails, labels, access legend).

MVUM inputs
- Download the MVUM Symbology shapefiles for roads and trails (files named `MVUM_Symbology_-_Motor_Vehicle_Use_Map_Roads.*` and `MVUM_Symbology_-_Motor_Vehicle_Use_Map_Trails.*`).
- Place all shapefile parts (.shp/.shx/.dbf/.prj/.cpg/.xml) in `projects/mvum/inputs/`; the folder is gitignored because the data exceeds GitHub's size limits.
