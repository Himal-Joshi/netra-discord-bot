from fluent.runtime import FluentBundle, FluentResource
from pathlib import Path
from typing import Dict

class I18nManager:
    def __init__(self, locales_dir: str = None):
        if locales_dir is None:
            locales_dir = Path(__file__).parent.parent / "locales"
        self.locales_dir = Path(locales_dir)
        self.bundles: Dict[str, FluentBundle] = {}
        self._load_locales()

    def _load_locales(self):
        for locale_path in self.locales_dir.iterdir():
            if locale_path.is_dir():
                locale = locale_path.name
                bundle = FluentBundle([locale])
                for ftl_file in locale_path.glob("*.ftl"):
                    with open(ftl_file, "r", encoding="utf-8") as f:
                        resource = FluentResource(f.read())
                        bundle.add_resource(resource)
                self.bundles[locale] = bundle

    def get(self, locale: str, key: str, **kwargs) -> str:
        bundle = self.bundles.get(locale, self.bundles.get("en"))
        if not bundle:
            return key

        message = bundle.get_message(key)
        if not message or not message.value:
            return key

        result, errors = bundle.format_pattern(message.value, kwargs)
        return result

i18n = I18nManager()
