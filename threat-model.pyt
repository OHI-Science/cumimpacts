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

        return [habitats_dir, threats_dir, matrix_file, output_dir]

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
        except:
            messages.AddErrorMessage(arcpy.GetMessages(2))
            messages.AddErrorMessage("Usage: threat_model_arcgis.py habitats_dir threats_dir matrix.csv output_dir")
            sys.exit(1)
        threat_model_arcgis.main(habitats_dir, threats_dir, matrix_file, output_dir)
