import importlib

from rest_framework import serializers
from rest_framework.serializers import SerializerMetaclass


class ModelDefaultSerializerMixin:
    def __init__(self, instance=None, *args, **kwargs):
        depth = kwargs.pop('depth', None)
        exclude = kwargs.pop('exclude', None)

        if exclude or depth is not None:
            meta = {k: v for k, v in self.Meta.__dict__.items() if not k.startswith('__')}
            if exclude:
                fields = meta.pop('fields', None)
                if fields != '__all__':
                    meta['fields'] = [x for x in fields if x not in set(exclude)]
                else:
                    meta |= {'exclude': exclude}

            if depth:
                meta |= {'depth': depth}
            self.Meta = type('Meta', (), meta)

        super().__init__(instance, *args, **kwargs)


class ModelDefaultSerializerMetaclass(SerializerMetaclass):
    def __new__(cls, name, bases, dct):
        if hasattr(model := dct['Meta'].model, 'default_serializer'):
            raise Exception(f'Default serializer for {model} already defined')
        model.default_serializer = property(
            lambda self: getattr(importlib.import_module(dct['__module__']), dct['__qualname__'])
        )

        return super().__new__(cls, name, (ModelDefaultSerializerMixin, serializers.ModelSerializer), dct)
