"""Entity naming: translated display names for the main entities."""

from .models import BluettiDevice, BluettiState

# fn_code -> translation key, per platform. The names live under
# "entity" in strings.json and translations/*.json.
TRANSLATED_NAMES: dict[str, dict[str, str]] = {
    "sensor": {
        "SOC": "soc",
        "PVAllTotalPower": "pvalltotalpower",
        "GridAllTotalPower": "gridalltotalpower",
        "ACLoadAllTotalPower": "acloadalltotalpower",
        "DCLoadAllTotalPower": "dcloadalltotalpower",
        "DsgFullTime": "dsgfulltime",
        "ChgFullTime": "chgfulltime",
        "InvWorkState": "invworkstate",
    },
    "switch": {
        "SetCtrlAc": "setctrlac",
        "SetCtrlStandby": "setctrlstandby",
        "SetCtrlDc": "setctrldc",
        "SetDCECO": "setdceco",
        "SetACECO": "setaceco",
    },
    "select": {
        "SetCtrlWorkModeBalco": "setctrlworkmodebalco",
    },
}


class BluettiEntityNameMixin:
    """Name an entity from the cloud, or from a translation for the main ones.

    A translated entity keeps the entity ID it would get from the cloud's
    English name, whatever the Home Assistant language.
    """

    _object_id_name: str | None = None

    def _set_entity_name(
        self, platform: str, device: BluettiDevice, state: BluettiState
    ) -> None:
        translation_key = TRANSLATED_NAMES[platform].get(state.fn_code)
        if translation_key is None or not state.fn_name:
            self._attr_name = f"{device.name} {state.fn_name}"
            return
        self._attr_has_entity_name = True
        self._attr_translation_key = translation_key
        self._object_id_name = state.fn_name

    @property
    def suggested_object_id(self) -> str | None:
        if self._object_id_name:
            return self._object_id_name
        return super().suggested_object_id
