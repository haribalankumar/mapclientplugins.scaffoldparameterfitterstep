import platform

import math

from opencmiss.zinc.field import Field

from .scaffoldmodel import ScaffoldModel
from .datamodel import DataModel
from ..utils import maths
from ..utils import zincutils

if platform.system() == 'Windows':
    WINDOWS_OS_FLAG = True
else:
    LINUX_OS_FLAG = True


def _read_model_description(region, description):
    stream_information = region.createStreaminformationRegion()
    memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements3D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements2D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(description['elements1D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(description['nodes'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)
    return stream_information


class MasterModel(object):

    def __init__(self,  aligner_description):

        self._description = aligner_description
        self._context = self._description.get_context()
        self._material_module = self._context.getMaterialmodule()
        self._region = self._description.get_scaffold_region()
        self._parameters = self._description.get_parameters()
        self._data_description = self._description.get_data_region_description()
        self._generator_settings = self._description.get_generator_settings()
        self._scaffold_coordinate_field = None
        self._data_coordinate_field = None

        self._scaffold_model = ScaffoldModel(self._context, self._region, None,
                                             self._material_module, self._parameters)
        self._data_model = DataModel(self._context, self._region, self._data_description, self._material_module)

        self._initialise_scaffold_and_data()
        self._scene = self._initialise_scene()
        self._settings_change_callback = None
        self._settings = dict(yaw=0.0, pitch=0.0, roll=0.0,
                              X=0.0, Y=0.0, Z=0.0)
        self._timekeeper = self._scene.getTimekeepermodule().getDefaultTimekeeper()
        self._current_time = None
        self._maximum_time = None
        self._time_sequence = None
        self._settings_change_callback = None
        self._current_angle_value = [0., 0., 0.]
        self._current_axis_value = [0., 0., 0.]

    def create_graphics(self, is_temporal):
        self._scaffold_model.create_scaffold_graphics()
        self._data_model.create_data_graphics(is_temporal)

    def get_context(self):
        return self._context

    def get_scaffold_parameters(self):
        return self._parameters

    def get_scaffold_type(self):
        return self._description.get_model_name()

    def get_species_type(self):
        return self._description.get_species()

    def get_scaffold_package_class(self):
        return self._description.get_scaffold_package()

    def get_generator_model(self):
        return self._description.get_generator_model()

    def get_generator_settings(self):
        return self._generator_settings

    def get_scene(self):
        if self._scene is not None:
            return self._scene
        else:
            raise ValueError('Scaffold scene is not initialised.')

    def get_yaw_value(self):
        return self._settings['yaw']

    def get_pitch_value(self):
        return self._settings['pitch']

    def get_roll_value(self):
        return self._settings['roll']

    def _initialise_scaffold_and_data(self):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        if self._data_coordinate_field is not None:
            self._data_coordinate_field = None

        self._scaffold_model.initialise_scaffold()
        self._data_model.initialise_data()
        self._scaffold_coordinate_field = self._scaffold_model.get_model_coordinate_field()
        self._data_coordinate_field = self._data_model.get_data_coordinate_field()

    def _initialise_scene(self):
        self._scaffold_model.initialise_scene()
        self._data_model.initialise_scene()
        return self._region.getScene()

    def set_settings_change_callback(self, settings_change_callback):
        self._settings_change_callback = settings_change_callback

    def set_time(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)

    def rotate_scaffold(self, angle, value):
        self._update_scaffold_coordinate_field()
        next_angle_value = value
        if angle == 'yaw':
            if next_angle_value > self._current_angle_value[0]:
                angle_value = next_angle_value - self._current_angle_value[0]
            else:
                angle_value = -(self._current_angle_value[0] - next_angle_value)
            euler_angles = [angle_value, 0., 0.]
            self._current_angle_value[0] = next_angle_value
            self._settings['yaw'] = next_angle_value
        elif angle == 'pitch':
            if next_angle_value > self._current_angle_value[1]:
                angle_value = next_angle_value - self._current_angle_value[1]
            else:
                angle_value = -(self._current_angle_value[1] - next_angle_value)
            euler_angles = [0., angle_value, 0.]
            self._current_angle_value[1] = next_angle_value
            self._settings['pitch'] = next_angle_value
        else:
            if next_angle_value > self._current_angle_value[2]:
                angle_value = next_angle_value - self._current_angle_value[2]
            else:
                angle_value = -(self._current_angle_value[2] - next_angle_value)
            euler_angles = [0., 0., angle_value]
            self._current_angle_value[2] = next_angle_value
            self._settings['roll'] = next_angle_value
        angles = euler_angles
        angles = [math.radians(x) for x in angles]
        rotation = maths.eulerToRotationMatrix3(angles)
        zincutils.transform_coordinates(self._scaffold_coordinate_field, rotation)
        self._apply_callback()

    def translate_scaffold(self, axis, value, rate):
        self._update_scaffold_coordinate_field()
        next_axis_value = value * rate

        if axis == 'X':
            if next_axis_value > self._current_axis_value[0]:
                axis_value = next_axis_value - self._current_axis_value[0]
            else:
                axis_value = -(self._current_axis_value[0] - next_axis_value)
            new_coordinates = [axis_value, 0., 0.]
            self._current_axis_value[0] = next_axis_value
            self._settings['X'] = next_axis_value
        elif axis == 'Y':
            if next_axis_value > self._current_axis_value[1]:
                angle_value = next_axis_value - self._current_axis_value[1]
            else:
                angle_value = -(self._current_axis_value[1] - next_axis_value)
            new_coordinates = [0., angle_value, 0.]
            self._current_axis_value[1] = next_axis_value
            self._settings['Y'] = next_axis_value
        else:
            if next_axis_value > self._current_axis_value[2]:
                angle_value = next_axis_value - self._current_axis_value[2]
            else:
                angle_value = -(self._current_axis_value[2] - next_axis_value)
            new_coordinates = [0., 0., angle_value]
            self._current_axis_value[2] = next_axis_value
            self._settings['Z'] = next_axis_value
        offset = new_coordinates
        zincutils.offset_scaffold(self._scaffold_coordinate_field, offset)
        self._apply_callback()

    def _update_scaffold_coordinate_field(self):
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def _apply_callback(self):
        self._settings_change_callback()
