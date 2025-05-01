import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias, Any

from environ import ImproperlyConfigured, environ, re
from smart_env import SmartEnv

from . import DEFAULTS

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    ItemValue: TypeAlias = str | bool | int | list[str] | None
    ConfigItem: TypeAlias = (
        tuple[type, ItemValue]  # type, value
        | tuple[type, ItemValue, str]  # type, value, help,
        | tuple[type, ItemValue, str, Any]  # type, value, hell, develop_value
    )


class Env(SmartEnv):
    def __init__(self, prefix: str, **scheme: "ConfigItem"):
        super().__init__(**scheme)
        self.prefix: str = prefix or ''

    def __getattr__(self, var):
        return self.get_value(var)

    def __copy__(self):
        return type(self)(self.prefix, **self.scheme)

    def as_dict(self):
        return {k: v for k, v in self.ENVIRON.items() if k.startswith(self.prefix)}

    def get_value(
        self,
        var,
        cast=None,
        default=environ.Env.NOTSET,  # noqa: C901
        parse_default=False,
        raw=False,
    ):
        """Return value for given environment variable.

        :param var: Name of variable.
        :param cast: Type to cast return value as.
        :param default: If var not present in environ, return this instead.
        :param parse_default: force to parse default..

        :returns: Value from environment or default (if set)
        """

        if raw:
            env_var = var
        else:
            env_var = f'{self.prefix}{var}'

        if var in self.scheme:
            var_info = self.scheme[var]

            try:
                has_default = len(var_info) == 2
            except TypeError:
                has_default = False

            if has_default:
                if not cast:
                    cast = var_info[0]

                if default is self.NOTSET:
                    default = var_info[1]
            else:
                if not cast:
                    cast = var_info

        try:
            value = self.ENVIRON[env_var]
        except KeyError:
            if default is self.NOTSET:
                error_msg = f'Set the {env_var} environment variable'
                raise ImproperlyConfigured(error_msg)

            value = default

        # Resolve any proxied values
        if hasattr(value, 'startswith') and '${' in value:
            m = environ.re.search(r'(\${(.*?)})', value)
            while m:
                value = re.sub(re.escape(m.group(1)), self.get_value(m.group(2), raw=True), value)
                m = environ.re.search(r'(\${(.*?)})', value)

        if value != default or (parse_default and value):
            value = self.parse_value(value, cast)

        return value

    def load_config(self, env_file: str = None):  # pragma: no cover
        # only used by test
        if not os.path.exists(env_file):
            raise ImproperlyConfigured(f"Configuration file '{env_file}' does not exists or cannot be read")
        # set defaults
        for key, value in DEFAULTS.items():
            self.ENVIRON.setdefault(f'{self.prefix}{key}', str(value[1]))

        try:
            content = Path(env_file).read_text()
        except IOError:  # pragma: no cover
            raise ImproperlyConfigured(f'{env_file} not found')

        for line in content.splitlines():
            m1 = re.match(r'\A([A-Za-z_0-9]+)=(.*)\Z', line)
            if m1:
                key, val = m1.group(1), m1.group(2)
                m2 = re.match(r"\A'(.*)'\Z", val)
                if m2:
                    val = m2.group(1)
                m3 = re.match(r'\A"(.*)"\Z', val)
                if m3:
                    val = re.sub(r'\\(.)', r'\1', m3.group(1))
                self.ENVIRON[f'{key}'] = str(val)

    def check_explicit(self) -> list[str]:
        missing = []
        for k, cfg in sorted(self.config.items()):
            if cfg["explicit"] and f'{self.prefix}{k}' not in self.ENVIRON:
                missing.append(k)
        return missing

    def set_environ_for_test(self, dic: dict) -> None:
        for key, conf in self.config.items():
            value = dic[key] if key in dic else conf['develop']
            os.environ[key] = str(value)



env = Env('KRM3_', **DEFAULTS)
