
"""
MAP Client Plugin Step
"""
import json

from PySide import QtGui

from mapclient.mountpoints.workflowstep import WorkflowStepMountPoint
from mapclientplugins.scaffoldparameterfitterstep.configuredialog import ConfigureDialog
from mapclientplugins.scaffoldparameterfitterstep.model.mastermodel import MasterModel
from mapclientplugins.scaffoldparameterfitterstep.view.scaffoldparameterfitterrwidget import ScaffoldParameterFitterWidget

class ScaffoldParameterFitterStep(WorkflowStepMountPoint):
    """
    Skeleton step which is intended to be a helpful starting point
    for new steps.
    """

    def __init__(self, location):
        super(ScaffoldParameterFitterStep, self).__init__('Scaffold Parameter Fitter', location)
        self._configured = False # A step cannot be executed until it has been configured.
        self._category = 'Fitting'
        # Add any other initialisation code here:
        self._icon =  QtGui.QImage(':/scaffoldparameterfitterstep/images/parametric_fitting_plugin.png')
        # Ports:
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#uses',
                      'model_description'))
        self.addPort(('http://physiomeproject.org/workflow/1.0/rdf-schema#port',
                      'http://physiomeproject.org/workflow/1.0/rdf-schema#provides',
                      '<not-set>'))
        # Port data:
        self._modelDescription = None  # model_description
        self._portData1 = None  # <not-set>
        # Config:
        self._config = {}
        self._view = None
        self._model = None
        self._alignerDescription = None
        self._generatorModelDescription = None
        self._config['identifier'] = ''

    def execute(self):
        """
        Add your code here that will kick off the execution of the step.
        Make sure you call the _doneExecution() method when finished.  This method
        may be connected up to a button in a widget for example.
        """
        # Put your execute step code here before calling the '_doneExecution' method.
        if self._view is None:
            context = 'ScaffoldParameterFitterContext'
            rigidAlignerDescription, modelDescription = self._modelDescription[0], self._modelDescription[1]
            scaffoldDescription = rigidAlignerDescription.get_scaffold_region_description()
            dataDescription = rigidAlignerDescription.get_data_region_description()
            self._model = MasterModel(context, [scaffoldDescription, dataDescription], modelDescription)
            self._view = ScaffoldParameterFitterWidget(self._model)
            self._view.register_done_execution(self._myDoneExecution)
            self._view.create_graphics(rigidAlignerDescription.data_is_temporal)

        self._setCurrentWidget(self._view)

    def _myDoneExecution(self):
        self._model = None
        self._view = None
        self._doneExecution()

    def setPortData(self, index, dataIn):
        """
        Add your code here that will set the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        uses port for this step then the index can be ignored.

        :param index: Index of the port to return.
        :param dataIn: The data to set for the port at the given index.
        """
        self._modelDescription = dataIn  # model_description

    def getPortData(self, index):
        """
        Add your code here that will return the appropriate objects for this step.
        The index is the index of the port in the port list.  If there is only one
        provides port for this step then the index can be ignored.

        :param index: Index of the port to return.
        """
        return self._portData1 # <not-set>

    def configure(self):
        """
        This function will be called when the configure icon on the step is
        clicked.  It is appropriate to display a configuration dialog at this
        time.  If the conditions for the configuration of this step are complete
        then set:
            self._configured = True
        """
        dlg = ConfigureDialog(self._main_window)
        dlg.identifierOccursCount = self._identifierOccursCount
        dlg.setConfig(self._config)
        dlg.validate()
        dlg.setModal(True)

        if dlg.exec_():
            self._config = dlg.getConfig()

        self._configured = dlg.validate()
        self._configuredObserver()

    def getIdentifier(self):
        """
        The identifier is a string that must be unique within a workflow.
        """
        return self._config['identifier']

    def setIdentifier(self, identifier):
        """
        The framework will set the identifier for this step when it is loaded.
        """
        self._config['identifier'] = identifier

    def serialize(self):
        """
        Add code to serialize this step to string.  This method should
        implement the opposite of 'deserialize'.
        """
        return json.dumps(self._config, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def deserialize(self, string):
        """
        Add code to deserialize this step from string.  This method should
        implement the opposite of 'serialize'.

        :param string: JSON representation of the configuration in a string.
        """
        self._config.update(json.loads(string))

        d = ConfigureDialog()
        d.identifierOccursCount = self._identifierOccursCount
        d.setConfig(self._config)
        self._configured = d.validate()


