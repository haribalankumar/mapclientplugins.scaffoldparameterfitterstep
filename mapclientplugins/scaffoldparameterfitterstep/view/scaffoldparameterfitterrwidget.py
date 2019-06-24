from PySide import QtGui

from .ui_scaffoldparameterfitterrwidget import Ui_ScaffoldParameterFitter

from opencmiss.zinchandlers.scenemanipulation import SceneManipulation
from opencmiss.zincwidgets.basesceneviewerwidget import BaseSceneviewerWidget


class ScaffoldParameterFitterWidget(QtGui.QWidget):

    def __init__(self, master_model, parent=None):
        super(ScaffoldParameterFitterWidget, self).__init__(parent)

        self._model = master_model

        self._ui = Ui_ScaffoldParameterFitter()
        self._ui.setupUi(self)
        self._setup_handlers()

        self._ui.sceneviewerWidget.set_context(self._model.get_context())

        self._done_callback = None
        self._settings = {'view-parameters': {}}
        self._model.set_settings_change_callback(self._setting_display)
        self._make_connections()

    def _make_connections(self):
        self._ui.sceneviewerWidget.graphics_initialized.connect(self._graphics_initialized)
        self._ui.meshType_label.setText(self._model.get_scaffold_type())
        self._ui.parameterSet_label.setText(self._model.get_species_type())

    def create_graphics(self, is_temporal):
        self._model.create_graphics(is_temporal)

    @staticmethod
    def _display_real(widget, value):
        new_text = '{:.4g}'.format(value)
        if isinstance(widget, QtGui.QDoubleSpinBox):
            widget.setValue(value)
        else:
            widget.setText(new_text)

    def _graphics_initialized(self):
        scene_viewer = self._ui.sceneviewerWidget.get_zinc_sceneviewer()
        self._refresh_scaffold_options()
        if scene_viewer is not None:
            scene = self._model.get_scene()
            self._ui.sceneviewerWidget.set_scene(scene)
            if len(self._settings['view-parameters']) == 0:
                self._view_all()
            else:
                eye = self._settings['view-parameters']['eye']
                look_at = self._settings['view-parameters']['look_at']
                up = self._settings['view-parameters']['up']
                angle = self._settings['view-parameters']['angle']
                self._ui.sceneviewerWidget.set_view_parameters(eye, look_at, up, angle)
                self._view_all()

    def register_done_execution(self, done_callback):
        self._done_callback = done_callback

    def _setup_handlers(self):
        basic_handler = SceneManipulation()
        self._ui.sceneviewerWidget.register_handler(basic_handler)

    def _setting_display(self):
        self._display_real(self._ui.yaw_doubleSpinBox, self._model.get_yaw_value())
        self._display_real(self._ui.pitch_doubleSpinBox, self._model.get_pitch_value())
        self._display_real(self._ui.roll_doubleSpinBox, self._model.get_roll_value())

    def _view_all(self):
        if self._ui.sceneviewerWidget.get_zinc_sceneviewer() is not None:
            self._ui.sceneviewerWidget.view_all()

    def _done_clicked(self):
        self._done_callback()

    def _refresh_scaffold_options(self):
        layout = self._ui.meshTypeOptions_frame.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        option_names = self._model.get_scaffold_parameters()
        for key, value in option_names.items():
            label = QtGui.QLabel(self._ui.meshTypeOptions_frame)
            label.setObjectName(key)
            label.setText(key)
            layout.addWidget(label)
            line_edit = QtGui.QLineEdit(self._ui.meshTypeOptions_frame)
            line_edit.setObjectName(key)
            line_edit.setText(str(value))
            layout.addWidget(line_edit)


