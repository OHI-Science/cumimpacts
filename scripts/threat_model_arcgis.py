#!/usr/bin/python
"""
  Threat Matrix Model

 
  Original Author: Matthew Perry and Shaun Walbirdge 
  ArcGIS port: Shaun Walbridge
  Mofified by: John Potapenko

python $PROJECT_DIR/code/threats/threat_model_arcgis.py $PROJECT_DIR/data/matrices/generated/all_med_annual_sst.csv model_all_med_annual_sst
"""

# ArcGIS implementation
import arcpy
from arcpy.sa import *
from arcpy import env

# Python system libraries
import sys
import os
import time

def setupEnvironment():
    # Check out the ArcGIS Spatial Analyst extension license
    try:
        arcpy.CheckOutExtension("Spatial")
    except:
        arcpy.AddError("Failed to check out the Spatial Analyst Extension which is required for this script.")
        sys.exit(1)
    
    # set environmental variables we'll need
    
    env.compression = 'LZW'
    # FIXME this should be a knob
    env.overwriteOutput = False
    # options at http://help.arcgis.com/en/arcgisdesktop/10.0/help/index.html#//001w0000001w000000.htm
    env.pyramid = "NONE"

def parseMatrix(matrix_file):
    try:
        arcpy.AddMessage("Reading matrix file...")
        fh = open(matrix_file, 'r')
        lines = fh.readlines()
    except:
        arcpy.AddError("Can't read matrix file")
        sys.exit(1)

    habitats = [h for h in lines[0].replace('\n','').replace('\r','').split(',')[1:] if h is not ""]
    threats = [] 
    matrix = {}
    for h in habitats:
        matrix[h] = {}
    arcpy.AddMessage("  matrix habitats found: %i" % len(habitats))
    #arcpy.AddMessage(habitats)

    for i in range(1, len(lines)):
        line = lines[i].replace('\n','').replace('\r','').split(',')
        threat = line[0]
        threats.append(threat)
        values = line[1:]
        #print "\n%s\n" % threat + "-" * 20
        weights = {}
        for j in range(0, len(habitats)):
            #arcpy.AddMessage("%s = %s" % (habitats[j], values[j]))
            matrix[habitats[j]][threat] = float(values[j])
    arcpy.AddMessage("  matrix threats found: %i" % len(threats))
    # arcpy.AddMessage(threats)
    # print matrix
    arcpy.AddMessage(matrix)

    return (matrix, habitats, threats)

def assignMatrixRasters(habitats, threats, habitats_dir, threats_dir):
    """
    Check that all files listed in the matrix file are actually present on disk:
      many of the problems encountered when running the model are due to this mismatch.

    For each raster found, record the full path to the raster so we can later use it in the
    map algebra step.
    """
    rasters = {'habitats' : dict.fromkeys(habitats), 
               'threats' : dict.fromkeys(threats)}
    dirs = {'habitats' : habitats_dir,
            'threats' : threats_dir}

    arcpy.AddMessage("Initializing rasters...")
    for type in rasters.keys():
        env.workspace = dirs[type]
        rasters_on_disk = arcpy.ListRasters()
        names = {}
        for raster in rasters_on_disk:
            (name, ext) = raster.split(".")
            names[name] = raster
        
        arcpy.AddMessage("  raster %s found: %i" % (type, len(names)))
        for raster in rasters[type].keys():
            # TODO what file types will be take in? do we need to check for all known types that
            # ArcGIS handles, or just a constrained set? 
    
            # check the file exists on disk
            if raster not in names.keys():
                arcpy.AddError("Missing %s!\n'%s' present in matrix, but no raster found." % (type, raster))
                sys.exit(1)
            else:
                rasters[type][raster] = Raster(names[raster])
    return rasters

def generateCombos(habitats, threats, rasters, output_dir, extent_file):
    """
    Generate a raster for each threat<->habitat combo
    """
    arcpy.AddMessage("Generating threat-habitat combos...")
    
    # Make sure our output directory has a spot for the combos
    try:
        combo_dir = os.path.sep.join([output_dir, 'combos'])
        if not os.path.exists(combo_dir):
            os.makedirs(combo_dir)
        env.workspace = combo_dir
        rasters_on_disk = arcpy.ListRasters()
    except Exception as e:
        arcpy.AddError("Failed to create directory for combos: %s" % combo_dir)
        arcpy.AddError("Exception: %s" % e)
        sys.exit(1)

    arcpy.env.extent=arcpy.Describe(extent_file).extent

    for habitat in habitats:
        arcpy.AddMessage("  generating combination rasters for: %s" % habitat)
        for threat in threats:
            name = "combo_%s_%s.tif" % (threat, habitat)
            threat_raster = rasters['threats'][threat]
            habitat_raster = rasters['habitats'][habitat]

            # FIXME: for now, skip existing
            if not name in rasters_on_disk:
                # arcpy.AddMessage("  writing: %s" % name)
                # both the inputs are cast as rasters, use 'em directly
                combo = threat_raster * habitat_raster

                # The save method automagically figures out the right type to save 
                # by looking at the extension. Sweet! 
                arcpy.CopyRaster_management(combo, name)
            else:
                pass
                arcpy.AddMessage("  skipping existing: %s" % name)
            """
            except:
                arcpy.AddError(arcpy.GetMessages())
                arcpy.AddError("Failed to generate combo for %s and %s" % (habitat, threat))
                sys.exit(1)
            """ 

def processAllCombosByHabitat(matrix, output_dir, set_null_zero, extent_file):
    habitat_combos = []

    combo_dir = "/".join([output_dir, 'combos'])

    # Make sure our output directory has a spot for the habitat_combos
    try:
        hab_dir = "/".join([output_dir, 'by_habitat'])
        if not os.path.exists(hab_dir):
            os.mkdir(hab_dir)
    except:
        arcpy.AddError("Failed to create directory for habitat combos: %s" % hab_dir)
        sys.exit(1)

    arcpy.AddMessage("Combining habitat combination rasters...")

    arcpy.env.extent=arcpy.Describe(extent_file).extent

    for habitat in matrix.keys():
        env.workspace = combo_dir
        arcpy.AddMessage("  combining %s" % habitat)

        habitat_combo_name = '%s_combo.tif' % habitat
        habitat_combo_path = "/".join([hab_dir, habitat_combo_name])
        # weighted terms now contains a list of habitat<->threat pairs for a specific _habitat_
        habitat_combos.append(habitat_combo_name)
            
        if not os.path.exists(habitat_combo_path):
            weighted_terms = []
            habitat_mapcalc = 0
            for threat in matrix[habitat].keys():
                name = "combo_%s_%s.tif" % (threat, habitat)
                weight = matrix[habitat][threat]
                # skip combos which are unweighted
                if int(weight) > 0:
                  if set_null_zero:
                    habitat_mapcalc = habitat_mapcalc + weight * Con(IsNull(Raster(name)),0,Raster(name))
                  else:
                    habitat_mapcalc = habitat_mapcalc + weight * Raster(name)

            arcpy.CopyRaster_management(habitat_mapcalc, habitat_combo_path)

            #habitat_compressed = arcpy.sa.ApplyEnvironment(habitat_mapcalc)
            #habitat_compressed.save(habitat_combo_path)
        else:
            arcpy.AddMessage("  skipping existing %s" % habitat_combo_name)

    env.workspace = hab_dir
    model_name = os.path.sep.join([output_dir, 'MODEL_sum_habitat_impacts.tif'])
    model_results = 0

    if not os.path.exists(model_name):
        for combo in habitat_combos:
            if set_null_zero:
              model_results=Con(IsNull(Raster(combo)),model_results,model_results+Raster(combo))
            else:
              model_results=model_results+Raster(combo)

        arcpy.CopyRaster_management(model_results, model_name) 
        arcpy.AddMessage("Model result saved to: %s" % model_name)
    else:
        arcpy.AddError("Existing model detected, overwrite not enabled: %s" % model_name)

def processAllCombosByThreat(matrix, output_dir, threats, habitats, rasters, avg_num_habitats, set_null_zero, extent_file):
    threat_combos = []

    combo_dir = "/".join([output_dir, 'combos'])

    # Make sure our output directory has a spot for the threat_combos
    try:
        threat_dir = "/".join([output_dir, 'by_threat'])
        if not os.path.exists(threat_dir):
            os.mkdir(threat_dir)
    except:
        arcpy.AddError("Failed to create directory for threat combos: %s" % threat_dir)
        sys.exit(1)

    arcpy.AddMessage("Combining threat combination rasters...")

    arcpy.env.extent=arcpy.Describe(extent_file).extent

    if avg_num_habitats:
      habitat_num = 0
      for habitat in habitats:
        habitat_num=habitat_num+Con(IsNull(rasters['habitats'][habitat]),0,rasters['habitats'][habitat])
      habitat_num=Con(habitat_num==0,1,habitat_num)
      arcpy.CopyRaster_management(habitat_num, os.path.sep.join([output_dir, 'habitat_num.tif']))

    for threat in threats:
        env.workspace = combo_dir
        arcpy.AddMessage("  combining %s" % threat)

        threat_combo_name = '%s_combo.tif' % threat
        threat_combo_path = "/".join([threat_dir, threat_combo_name])
        # weighted terms now contains a list of habitat<->threat pairs for a specific _threat_
        threat_combos.append(threat_combo_name)

        if not os.path.exists(threat_combo_path):
            weighted_terms = []
            threat_mapcalc = 0
            for habitat in matrix.keys():
                name = "combo_%s_%s.tif" % (threat, habitat)
                weight = matrix[habitat][threat]
                # skip combos which are unweighted
                if int(weight) > 0:
                  if set_null_zero:
                    threat_mapcalc = threat_mapcalc + weight * Con(IsNull(Raster(name)),0,Raster(name))
                  else:
                    threat_mapcalc = threat_mapcalc + weight * Raster(name)

            if avg_num_habitats:
              threat_mapcalc = threat_mapcalc/habitat_num

            # write this data out to our threat directory
            arcpy.CopyRaster_management(threat_mapcalc, threat_combo_path)
            #threat_compressed = arcpy.sa.ApplyEnvironment(threat_mapcalc)
            #threat_compressed.save(threat_combo_path)
        else:
            arcpy.AddMessage("  skipping existing %s" % threat_combo_name)

    env.workspace = threat_dir
    model_name = os.path.sep.join([output_dir, 'MODEL_sum_threat_impacts.tif'])
    model_results = 0

    if not os.path.exists(model_name):
        for combo in threat_combos:
            if set_null_zero:
              #new_rast=Con(IsNull(Raster(combo)),0,Raster(combo))
              #model_results=Con(IsNull(model_results),0,model_results)
              #model_results = model_results + new_rast
              model_results=Con(IsNull(Raster(combo)),model_results,model_results+Raster(combo))
            else:
              model_results=model_results+Raster(combo)

        arcpy.CopyRaster_management(model_results, model_name) 
        arcpy.AddMessage("Model result saved to: %s" % model_name)
    else:
        arcpy.AddError("Existing model detected, overwrite not enabled: %s" % model_name)

def doExtraSteps():
    """ extra analysis required for this process."""

    # statistics?
    # footprint?
    return

# calcRastersExtent: calculates extent of input rasters and puts result into output shapefile
#    in_raster_datasets: input rasters
#    Dest: output shapefile
def calcRastersExtent(in_raster_datasets,Dest):
  envOverwriteSetting=env.overwriteOutput
  env.overwriteOutput=True
  arcpy.CreateFeatureclass_management(os.path.dirname(Dest), os.path.basename(Dest), "POLYGON")
  arcpy.AddField_management(Dest,"RasterName", "String","","",250)

  cursor = arcpy.InsertCursor(Dest)
  point = arcpy.Point()
  array = arcpy.Array()
  corners = ["lowerLeft", "lowerRight", "upperRight", "upperLeft"]
  for Ras in in_raster_datasets:
    feat = cursor.newRow()
    r = arcpy.Raster(Ras)
    for corner in corners: 
      point.X = getattr(r.extent, "%s" % corner).X
      point.Y = getattr(r.extent, "%s" % corner).Y
      array.add(point)
    array.add(array.getObject(0))
    polygon = arcpy.Polygon(array)
    feat.shape = polygon
    feat.setValue("RasterName", Ras)
    cursor.insertRow(feat)
    array.removeAll()
  del feat
  del cursor
  env.overwriteOutput=envOverwriteSetting

# str2bool: convert string to boolean True/False
def str2bool(v):
    return v.lower() in ("yes", "true", "t", "1")

def main(habitats_dir, threats_dir, matrix_file, output_dir, by_threat, by_habitat, avg_num_habitats, set_null_zero):
    # set up the environment
    setupEnvironment()

    by_threat=str2bool(str(by_threat))
    by_habitat=str2bool(str(by_habitat))
    avg_num_habitats=str2bool(str(avg_num_habitats))
    set_null_zero=str2bool(str(set_null_zero))

    # TODO this should be replaced with a class, but this'll do for now.
    (matrix, habitats, threats) = parseMatrix(matrix_file)

    # check that all matrix items exist on the disk...
    # FIXME should use matrix directly instead of habs & threats, in class model.
    rasters = assignMatrixRasters(habitats, threats, habitats_dir, threats_dir)

    in_raster_datasets=[]
    for raster in rasters['habitats'].values():
      in_raster_datasets.append(os.path.join(habitats_dir,str(raster)))
    for raster in rasters['threats'].values():
      in_raster_datasets.append(os.path.join(threats_dir,str(raster)))
    extent_file=os.path.join(env.workspace,'raster_extent_temp.shp')
    calcRastersExtent(in_raster_datasets,extent_file)
    
    # generate combos, in the past this was handled in a separate step but needs to be done here
    generateCombos(habitats, threats, rasters, output_dir,extent_file)
    
    if by_habitat:
      processAllCombosByHabitat(matrix, output_dir, set_null_zero, extent_file)
    if by_threat:
      processAllCombosByThreat(matrix, output_dir, threats, habitats, rasters, avg_num_habitats, set_null_zero, extent_file)

    # FIXME we also want to generate the footprint maps, perhaps other things?
    # review the notes on this one...
    doExtraSteps()

if __name__ == "__main__":
    try:
        habitats_dir = sys.argv[1]
        threats_dir = sys.argv[2]
        matrix_file = sys.argv[3]
        output_dir = sys.argv[4]
        by_threat = sys.argv[5]
        by_habitat = sys.argv[6]
        avg_num_habitats = sys.argv[7]
        set_null_zero = sys.argv[8]
    except:
        print arcpy.GetMessages(2)
        print "Usage: threat_model_arcgis.py habitats_dir threats_dir matrix.csv output_dir by_threat by_habitat avg_num_habitats set_null_zero"
        sys.exit(1)

