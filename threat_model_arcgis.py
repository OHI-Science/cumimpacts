#!/usr/bin/python
"""
  Threat Matrix Model

 
  Original Author: Matthew Perry and Shaun Walbirdge 
  ArcGIS port: Shaun Walbridge

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

def generateCombos(habitats, threats, rasters, output_dir):
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

    """
    for habitat, data in matrix.items():
        for threat in data.keys():
            output = "combo_" + threat + "_" + habitat
    """
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
                arcpy.env.compression = 'LZW'
                arcpy.CopyRaster_management(combo, name)
                # combo_compressed.save(name)
            else:
                pass
                #arcpy.AddMessage("  skipping existing: %s" % name)
            """
            except:
                arcpy.AddError(arcpy.GetMessages())
                arcpy.AddError("Failed to generate combo for %s and %s" % (habitat, threat))
                sys.exit(1)
            """ 

def processAllCombos(matrix, output_dir):
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
                    habitat_mapcalc = habitat_mapcalc + weight * Raster(name)

            # write this data out to our habitat directory
            #habitat_compressed = arcpy.sa.ApplyEnvironment(habitat_mapcalc)
            arcpy.CopyRaster_management(habitat_mapcalc, habitat_combo_path)

            #habitat_compressed.save(habitat_combo_path)
        #else:
        #    arcpy.AddMessage("  skipping existing %s" % habitat_combo_name)

    env.workspace = hab_dir
    model_name = os.path.sep.join([output_dir, 'MODEL.tif'])
    model_results = 0

    if not os.path.exists(model_name):
        for combo in habitat_combos:
            model_results = model_results + Raster(combo)

        arcpy.CopyRaster_management(model_results, model_name) 
        arcpy.AddMessage("Model result saved to: %s" % model_name)
    else:
        arcpy.AddError("Existing model detected, overwrite not enabled: %s" % model_name)

def doExtraSteps():
    """ extra analysis required for this process."""

    # statistics?
    # footprint?
    return

def main(habitats_dir, threats_dir, matrix_file, output_dir):
    # set up the environment
    setupEnvironment()

    # TODO this should be replaced with a class, but this'll do for now.
    (matrix, habitats, threats) = parseMatrix(matrix_file)

    # check that all matrix items exist on the disk...
    # FIXME should use matrix directly instead of habs & threats, in class model.
    rasters = assignMatrixRasters(habitats, threats, habitats_dir, threats_dir)

    # generate combos, in the past this was handled in a separate step but needs to be done here
    generateCombos(habitats, threats, rasters, output_dir)
    
    processAllCombos(matrix, output_dir)

    # FIXME we also want to generate the footprint maps, perhaps other things?
    # review the notes on this one...
    doExtraSteps()

if __name__ == "__main__":
    try:
        habitats_dir = sys.argv[1]
        threats_dir = sys.argv[2]
        matrix_file = sys.argv[3]
        output_dir = sys.argv[4]
    except:
        print arcpy.GetMessages(2)
        print "Usage: threat_model_arcgis.py habitats_dir threats_dir matrix.csv output_dir"
        sys.exit(1)

