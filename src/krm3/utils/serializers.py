import importlib

from rest_framework import serializers
from rest_framework.serializers import SerializerMetaclass


class ModelDefaultSerializerMixin:
    def __init__(self, instance=None, *args, **kwargs):  # noqa: ANN001, ANN204
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
    def __new__(cls, name, bases, dct):  # noqa: ANN001, ANN204
        if hasattr(model := dct['Meta'].model, 'default_serializer'):
            raise Exception(f'Default serializer for {model} already defined')
        model.default_serializer = property(
            lambda self: getattr(importlib.import_module(dct['__module__']), dct['__qualname__'])
        )

        return super().__new__(cls, name, (ModelDefaultSerializerMixin, serializers.ModelSerializer), dct)


class PrivateMediaFileField(serializers.FileField):
    """File field for files in `PrivateMediaStorage`, whose storage refuses to build URLs.

    The file is rendered with the model property returning the authenticated URL (e.g. 'image_url' for
    Expense), like `krm3.core.widgets.PrivateMediaFileInput` does in forms. Uploads work as for a FileField.
    """

    def __init__(self, url_field: str, **kwargs) -> None:  # noqa: ANN003
        self.url_field = url_field
        super().__init__(**kwargs)

    def to_representation(self, value):  # noqa: ANN001, ANN201
        if not value:
            return None
        url = getattr(value.instance, self.url_field)
        request = self.context.get('request')
        if url and request is not None:
            return request.build_absolute_uri(url)
        return url
