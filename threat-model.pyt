# -*- coding: utf-8 -*-

import os
import sys

import arcpy

# import our local directory so we can import internal modules
local_path = os.path.dirname(__file__)
sys.path.insert(0, local_path)

class Toolbox(object):
    def __init__(self):
        self.label = u'Threat Model'
        self.alias = ''
        self.tools = [ThreatModel]

# Tool implementation code

class ThreatModel(object):
    def __init__(self):
        self.label = u'Threat Model'
        self.description = u'Run the Threat Model, which evaluates a matrix of threat-habitat pairings, and produces a output model and a set of statistics.'
        self.canRunInBackground = False

    def getParameterInfo(self):
        # Habitats_Folder
        habitats_dir = arcpy.Parameter()
        habitats_dir.name = u'Habitats_Folder'
        habitats_dir.displayName = u'Habitats Folder'
        habitats_dir.parameterType = 'Required'
        habitats_dir.direction = 'Input'
        habitats_dir.datatype = u'Folder'

        # Threats_Folder
        threats_dir = arcpy.Parameter()
        threats_dir.name = u'Threats_Folder'
        threats_dir.displayName = u'Threats Folder'
        threats_dir.parameterType = 'Required'
        threats_dir.direction = 'Input'
        threats_dir.datatype = u'Folder'

        # Matrix_CSV
        matrix_file = arcpy.Parameter()
        matrix_file.name = u'Matrix_CSV'
        matrix_file.displayName = u'Matrix CSV'
        matrix_file.parameterType = 'Required'
        matrix_file.direction = 'Input'
        matrix_file.datatype = u'File'

        # matrix CSV must be of a type we parse
        matrix_file.filter.list = ['csv', 'txt']

        # Output_Folder
        output_dir= arcpy.Parameter()
        output_dir.name = u'Output_Folder'
        output_dir.displayName = u'Output Folder'
        output_dir.parameterType = 'Required'
        output_dir.direction = 'Output'
        output_dir.datatype = u'Folder'

	# Boolean: create by_threat layers
	by_threat=arcpy.Parameter()
	by_threat.name=u'By Threat'
	by_threat.displayName=u'Calculate impacts from individual threats'
	by_threat.parameterType='Optional'
	by_threat.direction='Input'
	by_threat.datatype=u'Boolean'

	# Boolean: create by_habitat layers
	by_habitat=arcpy.Parameter()
	by_habitat.name=u'By Habitat'
	by_habitat.displayName=u'Calculate impacts on individual habitats'
	by_habitat.parameterType='Optional'
	by_habitat.direction='Input'
	by_habitat.datatype=u'Boolean'
	
	# Boolean: average by number of habitats
	avg_num_habitats=arcpy.Parameter()
	avg_num_habitats.name=u'Average Num Habitats'
	avg_num_habitats.displayName=u'Average impacts by number of habitats'
	avg_num_habitats.parameterType='Optional'
	avg_num_habitats.direction='Input'
	avg_num_habitats.datatype=u'Boolean'
	
	# Boolean: treat NoData as zero
	set_null_zero=arcpy.Parameter()
	set_null_zero.name=u'Set Null Zero'
	set_null_zero.displayName=u'Treat NoData values as zeros'
	set_null_zero.parameterType='Optional'
	set_null_zero.direction='Input'
	set_null_zero.datatype=u'Boolean'

        return [habitats_dir, threats_dir, matrix_file, output_dir, by_threat, by_habitat, avg_num_habitats, set_null_zero]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateParameters()

    def updateMessages(self, parameters):
        validator = getattr(self, 'ToolValidator', None)
        if validator:
             return validator(parameters).updateMessages()

    def execute(self, parameters, messages):
        from code import threat_model_arcgis
        try:
            habitats_dir = parameters[0].valueAsText
            threats_dir = parameters[1].valueAsText
            matrix_file = parameters[2].valueAsText
            output_dir = parameters[3].valueAsText
            by_threat = parameters[4].valueAsText
            by_habitat = parameters[5].valueAsText
            avg_num_habitats = parameters[6].valueAsText
            set_null_zero = parameters[7].valueAsText
        except:
            messages.AddErrorMessage(arcpy.GetMessages(2))
            messages.AddErrorMessage("Usage: threat_model_arcgis.py habitats_dir threats_dir matrix.csv output_dir by_threat by_habitat avg_num_habitats set_null_zero")
            sys.exit(1)
	reload(threat_model_arcgis)
        threat_model_arcgis.main(habitats_dir, threats_dir, matrix_file, output_dir, by_threat, by_habitat, avg_num_habitats, set_null_zero)
