import platform

import math

from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK

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

    def __init__(self, aligner_description, is_temporal):

        self._description = aligner_description
        self._context = self._description.get_context()
        self._material_module = self._context.getMaterialmodule()
        self._region = self._description.get_scaffold_region()
        self._parameters = self._description.get_parameters()
        self._data_description = self._description.get_data_region_description()
        self._generator_settings = self._description.get_generator_settings()
        self._generator_model = self._description.get_generator_model()
        self._scaffold_package = self._description.get_scaffold_package()
        self._scaffold_package_class = self._description.get_scaffold_package_class()

        self._scaffold_coordinate_field = None
        self._data_coordinate_field = None
        self._scaffold_data_scale_ratio = None

        self._scaffold_model = ScaffoldModel(self._context, self._region, self._generator_model,
                                             self._parameters, self._material_module,
                                             self._scaffold_package, self._scaffold_package_class)

        self._data_model = DataModel(self._context, self._region, self._data_description,
                                     self._material_module, is_temporal)

        self._initialise_scaffold_and_data()
        self._scene = self._initialise_scene()
        self._settings_change_callback = None
        self._settings = self._description.get_aligner_settings()
        self._timekeeper = self._context.getTimekeepermodule().getDefaultTimekeeper()
        self._current_time = None
        self._maximum_time = None
        self._time_sequence = None
        self._settings_change_callback = None
        self._current_angle_value = [0., 0., 0.]
        self._current_axis_value = [0., 0., 0.]

    def update_scaffold(self):
        self._scaffold_model.generate_mesh_for_fitting()

    def get_edit_scaffold(self, key):
        return self._scaffold_model.get_edit_scaffold_option(key)

    def generate_mesh(self):
        self._scaffold_model.generate_mesh_for_fitting()

    def create_graphics(self, is_temporal):
        self._scaffold_model.create_scaffold_graphics()
        self._data_model.create_data_graphics(is_temporal)

    def set_time_value(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)
        self._data_model.set_time(time)

    def set_max_time(self, time):
        self._maximum_time = time

    def get_context(self):
        return self._context

    def get_scaffold_parameters(self):
        return self._parameters

    def get_scaffold_type(self):
        return self._description.get_model_name()

    def get_species_type(self):
        return self._description.get_species()

    def get_scaffold_package(self):
        return self._scaffold_model.get_scaffold_package()

    def get_scaffold_package_class(self):
        return self._scaffold_package_class

    def get_generator_model(self):
        return self._generator_model

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
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()
        self._data_coordinate_field = self._data_model.get_data_coordinate_field()

    def _initialise_scene(self):
        self._scaffold_model.initialise_scene()
        self._data_model.initialise_scene()
        return self._region.getScene()

    def initialise_time_graphics(self, time):
        self._timekeeper.setTime(time)

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
        zincutils.transform_coordinates(self._scaffold_coordinate_field, rotation, time=self._current_time)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)
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
        zincutils.offset_scaffold(self._scaffold_coordinate_field, offset, time=self._current_time)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)
        self._apply_callback()

    def _update_scaffold_coordinate_field(self):
        self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()

    def get_scaffold_to_data_ratio(self):
        correction_factor = self._description.get_correction_factor()
        if correction_factor is not None:
            print('Current time = ', self._current_time)
            data_range_temp = self._data_model.get_scale(self._current_time)

            for range_index in range(len(data_range_temp)):
                if data_range_temp[range_index] == 0.0:
                    data_range_temp[range_index] = 1.0

            data_range = maths.eldiv(data_range_temp, correction_factor)
            scaffold_scale = self._scaffold_model.get_scale()
            diff = maths.eldiv(scaffold_scale, data_range)

            for temp_index in range(len(diff)):
                if diff[temp_index] == scaffold_scale[temp_index]:
                    diff[temp_index] = 1.0
        else:
            data_scale = self._data_model.get_scale(self._current_time)
            scaffold_scale = self._scaffold_model.get_scale()
            diff = maths.eldiv(scaffold_scale, data_scale)

        self._scaffold_data_scale_ratio = diff
        mean_diff = sum(diff) / len(diff)
        diff_string = '%s*%s*%s' %(diff[0], diff[1], diff[2])
        return mean_diff, diff_string

    def _apply_scale(self):

        scale = self._scaffold_data_scale_ratio
        print('scale before average = ', scale)
        if scale[0] == 1.0:
            scale[0] = (scale[1] + scale[2]) / 2
        elif scale[1] == 1.0:
            scale[1] = (scale[0] + scale[2]) / 2
        elif scale[2] == 1.0:
            scale[2] = (scale[0] + scale[1]) / 2

        mean_diff = sum(scale) / len(scale)

        # Scaling factor scaffold
        # scale_scaffold = [1.0 / x for x in scale]
        scale_scaffold = 1.0 / mean_diff
        print('scale after average = ', scale_scaffold)

        zincutils.scale_coordinates(self._scaffold_coordinate_field, [scale_scaffold]*3, time=self._current_time)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)

    def _get_model_centre(self):
        model_minimums, model_maximums = self._scaffold_model.get_range(time=self._current_time)
        model_centre_temp = maths.mult(maths.add(model_minimums, model_maximums), 0.5)
        model_centre = maths.eldiv(model_centre_temp, [1, 1, 1])
        return model_centre

    def scale_scaffold(self, all_time_points=False):
        self._reference_centre = self._get_model_centre()
        if self._scaffold_data_scale_ratio is None:
            if all_time_points:
                for time in range(self._maximum_time):
                    self.set_time_value(time)
                    self.get_scaffold_to_data_ratio()
                    self._apply_scale()
                    self._align_scaffold_on_data()
            else:
                self.get_scaffold_to_data_ratio()
                self._apply_scale()
                # self._align_scaffold_on_data()
        else:
            self._scaffold_coordinate_field = None
            self._scaffold_coordinate_field = self._scaffold_model.get_coordinate_field()
            self._scaffold_data_scale_ratio = None
            if all_time_points:
                for time in range(self._maximum_time):
                    self.set_time_value(time)
                    self.get_scaffold_to_data_ratio()
                    self._apply_scale()
                    # self._align_scaffold_on_data()
            else:
                self.get_scaffold_to_data_ratio()
                self._apply_scale()
                # self._align_scaffold_on_data()

    def _align_scaffold_on_data(self):
        data_minimums, data_maximums = self._data_model.get_range(time=self._current_time)
        data_centre = maths.mult(maths.add(data_minimums, data_maximums), 0.5)
        model_minimums, model_maximums = self._scaffold_model.get_range(time=self._current_time)
        model_centre_temp = maths.mult(maths.add(model_minimums, model_maximums), 0.5)
        model_centre = maths.eldiv(model_centre_temp, [1, 1, 1])
        offset = maths.sub(self._reference_centre, model_centre_temp)
        zincutils.offset_scaffold(self._scaffold_coordinate_field, offset, time=self._current_time)
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)

        time = self._current_time
        exf_file = 'fitted_heart_%s.exf' % time
        self._region.writeFile('D:\\sparc\\tmp\\pig_scaffold_time\\{}'.format(exf_file))

    def _apply_callback(self):
        self._settings_change_callback()

    def save_temp(self):
        filename = 'fitted_heart_%.3f' % self._current_time
        self._region.writeFile('D:\\sparc\\tmp\\pig_scaffold_time\\{}'.format(filename))
