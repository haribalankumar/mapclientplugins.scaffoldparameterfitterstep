import json
import platform

import math

from opencmiss.zinc.context import Context
from opencmiss.zinc.field import Field
from opencmiss.zinc.status import OK as ZINC_OK
from opencmiss.zinc.streamregion import StreaminformationRegion

from .scaffoldmodel import ScaffoldModel
from .datamodel import DataModel
from ..utils import maths
from ..utils import zincutils

if platform.system() == 'Windows':
    WINDOWS_OS_FLAG = True
else:
    LINUX_OS_FLAG = True


def _read_aligner_description(scaffold_region, data_region, scaffold_description, data_description):
    scaffold_stream_information = scaffold_region.createStreaminformationRegion()
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements3D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements2D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements1D'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)
    memory_resource = scaffold_stream_information.createStreamresourceMemoryBuffer(scaffold_description['nodes'])
    scaffold_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)

    data_stream_information = data_region.createStreaminformationRegion()

    for key in data_description:
        if key != 'elements3D' and key != 'elements2D' and key != 'elements1D' and key != 'nodes':
            if isinstance(key, float):
                time = key
            else:
                time = float(key)

            memory_resource = data_stream_information.createStreamresourceMemoryBuffer(data_description[key])
            data_stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
            data_stream_information.setResourceAttributeReal(memory_resource, StreaminformationRegion.ATTRIBUTE_TIME,
                                                             time)
    return scaffold_stream_information, data_stream_information


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

    def __init__(self, context, aligner_description, model_description):

        self._context = Context(context)
        self._material_module = self._context.getMaterialmodule()

        # self._region = self._context.getDefaultRegion()
        self._region = self._context.createRegion()
        self._region.setName('parent_region')

        self._initial_scaffold_region = self._region.createChild('scaffold_region')
        self._initial_data_region = self._region.createChild('datapoint_region')

        self._scaffold_coordinate_field = None
        self._data_coordinate_field = None

        scaffold_description, data_description = aligner_description[0], aligner_description[1]

        self._scaffold_stream_information, self._data_stream_information = _read_aligner_description(
            self._initial_scaffold_region, self._initial_data_region, scaffold_description, data_description)

        self._generator_model_description = model_description

        self._scaffold_model = ScaffoldModel(self._context, self._initial_scaffold_region, self._material_module,
                                             self._generator_model_description.get_parameters())
        self._data_model = DataModel(self._context, self._initial_data_region, self._material_module)

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

    def get_streams(self):
        return self._scaffold_stream_information, self._data_stream_information

    def get_scaffold_parameters(self):
        return self._generator_model_description.get_parameters()

    def get_scaffold_type(self):
        return self._generator_model_description.get_model_name()

    def get_species_type(self):
        return self._generator_model_description.get_model_species()

    def get_scaffold_package_class(self):
        return self._generator_model_description.get_scaffold_package()

    def get_generator_model(self):
        return self._generator_model_description.get_generator()

    def _get_mesh(self):
        fm = self._initial_scaffold_region.getFieldmodule()
        for dimension in range(3, 0, -1):
            mesh = fm.findMeshByDimension(dimension)
            if mesh.getSize() > 0:
                return mesh
        raise ValueError('Model contains no mesh')

    def _get_model_coordinate_field(self):
        mesh = self._get_mesh()
        element = mesh.createElementiterator().next()
        if not element.isValid():
            raise ValueError('Model contains no elements')
        fm = self._initial_scaffold_region.getFieldmodule()
        cache = fm.createFieldcache()
        cache.setElement(element)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine model coordinate field')

    def _get_data_coordinate_field(self):
        fm = self._initial_data_region.getFieldmodule()
        data_point_set = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        data_point = data_point_set.createNodeiterator().next()
        if not data_point.isValid():
            raise ValueError('Data cloud is empty')
        cache = fm.createFieldcache()
        cache.setNode(data_point)
        field_iter = fm.createFielditerator()
        field = field_iter.next()
        while field.isValid():
            if field.isTypeCoordinate() and (field.getNumberOfComponents() <= 3):
                if field.isDefinedAtLocation(cache):
                    return field
            field = field_iter.next()
        raise ValueError('Could not determine data coordinate field')

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

    def initialise_scaffold_and_data(self, scaffold_stream, data_stream):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        result = self._initial_scaffold_region.read(scaffold_stream)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise scaffold.')

        if self._data_coordinate_field is not None:
            self._data_coordinate_field = None
        result = self._initial_data_region.read(data_stream)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise data cloud.')

        self._scaffold_coordinate_field = self._get_model_coordinate_field()
        self._data_coordinate_field = self._get_data_coordinate_field()
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)
        self._data_model.set_coordinate_field(self._data_coordinate_field)

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
        # self._scaffold_model.set_scaffold_graphics_post_rotate(self._transformed_scaffold_field)
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
