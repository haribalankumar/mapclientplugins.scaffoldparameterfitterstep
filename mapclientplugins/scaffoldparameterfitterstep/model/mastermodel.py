import json
import platform

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


def _read_aligner_description(region, scaffold_description, data_description):
    stream_information = region.createStreaminformationRegion()
    memory_resource = stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements3D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH3D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements2D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH2D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(scaffold_description['elements1D'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_MESH1D)
    memory_resource = stream_information.createStreamresourceMemoryBuffer(scaffold_description['nodes'])
    stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_NODES)

    for key in data_description:
        if key != 'elements3D' and key != 'elements2D' and key != 'elements1D' and key != 'nodes':
            if isinstance(key, float):
                time = key
            else:
                time = float(key)

            memory_resource = stream_information.createStreamresourceMemoryBuffer(data_description[key])
            stream_information.setResourceDomainTypes(memory_resource, Field.DOMAIN_TYPE_DATAPOINTS)
            stream_information.setResourceAttributeReal(memory_resource, StreaminformationRegion.ATTRIBUTE_TIME,
                                                        time)
    return stream_information


class MasterModel(object):

    def __init__(self, context, aligner_description, model_description):

        self._context = Context(context)
        self._material_module = self._context.getMaterialmodule()
        self._region = self._context.createRegion()
        self._region.setName('parameter_fitting_region')

        self._scaffold_coordinate_field = None
        self._data_coordinate_field = None

        scaffold_description, data_description = aligner_description[0], aligner_description[1]
        self._stream_information = _read_aligner_description(self._region, scaffold_description, data_description)
        self._scene = self._initialise_scene()

        self._scaffold_model = ScaffoldModel(self._context, self._region, self._material_module)
        self._data_model = DataModel(self._context, self._region, self._material_module)
        self._scaffold_model.set_scene(self._scene)
        self._data_model.set_scene(self._scene)

        self._settings_change_callback = None

        self._settings = dict(yaw=0.0, pitch=0.0, roll=0.0)

        self._timekeeper = self._scene.getTimekeepermodule().getDefaultTimekeeper()
        self._current_time = None
        self._maximum_time = None
        self._time_sequence = None

    def create_graphics(self, is_temporal):
        self._scaffold_model.create_scaffold_graphics()
        self._data_model.create_data_graphics(is_temporal)

    def get_context(self):
        return self._context

    def get_stream(self):
        return self._stream_information

    def _get_mesh(self):
        fm = self._region.getFieldmodule()
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
        fm = self._region.getFieldmodule()
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
        fm = self._region.getFieldmodule()
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

    def initialise_scaffold_and_data(self, stream):
        if self._scaffold_coordinate_field is not None:
            self._scaffold_coordinate_field = None
        if self._data_coordinate_field is not None:
            self._data_coordinate_field = None
        result = self._region.read(stream)
        if result != ZINC_OK:
            raise ValueError('Failed to read and initialise scaffold or data.')
        self._scaffold_coordinate_field = self._get_model_coordinate_field()
        self._data_coordinate_field = self._get_data_coordinate_field()
        self._scaffold_model.set_coordinate_field(self._scaffold_coordinate_field)
        self._data_model.set_coordinate_field(self._data_coordinate_field)

    def _initialise_scene(self):
        return self._region.getScene()

    def set_settings_change_callback(self, settings_change_callback):
        self._settings_change_callback = settings_change_callback

    def set_time(self, time):
        self._current_time = time
        self._timekeeper.setTime(time)
