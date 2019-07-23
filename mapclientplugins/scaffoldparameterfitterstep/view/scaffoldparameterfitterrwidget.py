from functools import partial

from PySide import QtGui

from .ui_scaffoldparameterfitterrwidget import Ui_ScaffoldParameterFitter

from opencmiss.zinchandlers.scenemanipulation import SceneManipulation


class ScaffoldParameterFitterWidget(QtGui.QWidget):

    def __init__(self, master_model, shareable_widget, is_temporal, max_time, parent=None):
        super(ScaffoldParameterFitterWidget, self).__init__(parent)

        self._model = master_model
        self._scaffold_package = self._model.get_scaffold_package()
        self._scaffold_package_class = self._model.get_scaffold_package_class()
        self._generator_model = self._model.get_generator_model()
        self._generator_settings = self._model.get_generator_settings()
        self._ui = Ui_ScaffoldParameterFitter()
        self._ui.setupUi(self, shareable_widget)
        self._setup_handlers()
        self._is_temporal = is_temporal

        if self._is_temporal:
            self._ui.timePoint_spinBox.setEnabled(True)
            self._ui.timePoint_spinBox.setMaximum(max_time)
            self._model.set_max_time(max_time)

        self._ui.sceneviewerWidget.setContext(self._model.get_context())

        self._done_callback = None
        self._scene_change_callback = None
        self._settings = {'view-parameters': {}}
        self._model.set_settings_change_callback(self._setting_display)
        self._make_connections()

    def _make_connections(self):
        self._ui.sceneviewerWidget.graphicsInitialized.connect(self._graphics_initialized)
        self._ui.meshType_label.setText(self._model.get_scaffold_type())
        self._ui.parameterSet_label.setText(self._model.get_species_type())

        self._ui.timePoint_spinBox.valueChanged.connect(self._time_changed)

        self._ui.yaw_doubleSpinBox.valueChanged.connect(self._yaw_clicked)
        self._ui.pitch_doubleSpinBox.valueChanged.connect(self._pitch_clicked)
        self._ui.roll_doubleSpinBox.valueChanged.connect(self._roll_clicked)
        self._ui.positionX_doubleSpinBox.valueChanged.connect(self._x_clicked)
        self._ui.positionY_doubleSpinBox.valueChanged.connect(self._y_clicked)
        self._ui.positionZ_doubleSpinBox.valueChanged.connect(self._z_clicked)

        self._ui.fit_pushButton.setEnabled(True)
        if self._is_temporal:
            self._ui.fit_pushButton.clicked.connect(self._scale)
        else:
            self._ui.fit_pushButton.clicked.connect(self._fit)

        self._ui.saveSettingsButton.clicked.connect(self._save_temp)

    def _save_temp(self):
        self._model.save_temp()

    def get_scaffold_package(self):
        return self._model.get_scaffold_package()

    def create_graphics(self, is_temporal):
        if self._is_temporal is None:
            self._is_temporal = is_temporal
        self._model.create_graphics(is_temporal)
        self._model.set_time_value(0.0)
        self._model.initialise_time_graphics(0.0)

    @staticmethod
    def _display_real(widget, value):
        new_text = '{:.4g}'.format(value)
        if isinstance(widget, QtGui.QDoubleSpinBox):
            widget.setValue(value)
        else:
            widget.setText(new_text)

    def _graphics_initialized(self):
        # scene_viewer = self._ui.sceneviewerWidget.get_zinc_sceneviewer()
        scene_viewer = self._ui.sceneviewerWidget.getSceneviewer()
        self._refresh_scaffold_options()
        if scene_viewer is not None:
            scene = self._model.get_scene()
            # self._ui.sceneviewerWidget.set_scene(scene)
            self._ui.sceneviewerWidget.setScene(scene)
            if len(self._settings['view-parameters']) == 0:
                self._view_all()
            else:
                eye = self._settings['view-parameters']['eye']
                look_at = self._settings['view-parameters']['look_at']
                up = self._settings['view-parameters']['up']
                angle = self._settings['view-parameters']['angle']
                # self._ui.sceneviewerWidget.set_view_parameters(eye, look_at, up, angle)
                self._ui.sceneviewerWidget.setViewParameters(eye, look_at, up, angle)
                self._view_all()

    def register_done_execution(self, done_callback):
        self._done_callback = done_callback

    def register_scene_change_callback(self, scene_change_callback):
        self._scene_change_callback = scene_change_callback

    def _setup_handlers(self):
        basic_handler = SceneManipulation()
        # self._ui.sceneviewerWidget.register_handler(basic_handler)

    def _setting_display(self):
        self._display_real(self._ui.yaw_doubleSpinBox, self._model.get_yaw_value())
        self._display_real(self._ui.pitch_doubleSpinBox, self._model.get_pitch_value())
        self._display_real(self._ui.roll_doubleSpinBox, self._model.get_roll_value())

    def _view_all(self):
        if self._ui.sceneviewerWidget.getSceneviewer() is not None:
            # self._ui.sceneviewerWidget.view_all()
            self._ui.sceneviewerWidget.viewAll()

    def _done_clicked(self):
        self._done_callback()

    def _scaffold_parameter_changed(self, line_edit):
        if line_edit.objectName() == 'scale':
            self._generator_settings[line_edit] = line_edit.text()
            # dependent_changes = self._generator_model.setSettings(self._generator_settings, change_scene=False)
        else:
            # dependent_changes = self._generator_model.setScaffoldOption(line_edit.objectName(),
            #                                                             line_edit.text(),
            #                                                             change_scene=False)
            # new_region = self._generator_model.generate_mesh_for_fitting(self._scaffold_package_class)
            # self._model.set_option(line_edit.objectName(), line_edit.text())
            self._model.generate_mesh()
            final_value = self._model.get_edit_scaffold(line_edit.objectName())
            line_edit.setText(str(final_value))
        # if dependent_changes:
        #     self._refresh_scaffold_options()
        # else:

    def _refresh_scaffold_options(self):
        layout = self._ui.meshTypeOptions_frame.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        custom_option_names = self._model.get_scaffold_parameters()
        option_names = self._scaffold_package.getScaffoldType().getOrderedOptionNames()
        option_names.append('scale')
        for key in option_names:
            if key in custom_option_names.keys():
                value = custom_option_names[key]
                label = QtGui.QLabel(self._ui.meshTypeOptions_frame)
                label.setObjectName(key)
                label.setText(key)
                layout.addWidget(label)
                if isinstance(value, self._scaffold_package_class):
                    push_button = QtGui.QPushButton()
                    push_button.setObjectName(key)
                    push_button.setText('Edit >>')
                    callback = partial(self._meshTypeOptionScaffoldPackageButtonPressed, push_button)
                    push_button.clicked.connect(callback)
                    layout.addWidget(push_button)
                else:
                    line_edit = QtGui.QLineEdit(self._ui.meshTypeOptions_frame)
                    line_edit.setObjectName(key)
                    line_edit.setText(str(value))
                    callback = partial(self._scaffold_parameter_changed, line_edit)
                    line_edit.editingFinished.connect(callback)
                    layout.addWidget(line_edit)

    def _time_changed(self):
        time_value = self._ui.timePoint_spinBox.value()
        self._model.set_time_value(time_value)

    def _yaw_clicked(self):
        value = self._ui.yaw_doubleSpinBox.value()
        self._model.rotate_scaffold('yaw', value)

    def _pitch_clicked(self):
        value = self._ui.pitch_doubleSpinBox.value()
        self._model.rotate_scaffold('pitch', value)

    def _roll_clicked(self):
        value = self._ui.roll_doubleSpinBox.value()
        self._model.rotate_scaffold('roll', value)

    def _x_clicked(self):
        value = self._ui.positionX_doubleSpinBox.value()
        rate = self._ui.rateOfChange_horizontalSlider.value()
        self._model.translate_scaffold('X', value, rate)

    def _y_clicked(self):
        value = self._ui.positionY_doubleSpinBox.value()
        rate = self._ui.rateOfChange_horizontalSlider.value()
        self._model.translate_scaffold('Y', value, rate)

    def _z_clicked(self):
        value = self._ui.positionZ_doubleSpinBox.value()
        rate = self._ui.rateOfChange_horizontalSlider.value()
        self._model.translate_scaffold('Z', value, rate)

    def _scale(self):
        if self._ui.fitAllTime_radioButton.isChecked():
            self._model.scale_scaffold(all_time_points=True)
        else:
            self._model.scale_scaffold()

    def _fit(self):
        pass
