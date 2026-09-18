from dataclasses import dataclass


@dataclass
class ModelRoute:
    type: str
    label: str
    api_key_env: str
    model: str
    base_url: str | None = None
    enabled: bool = True
    function_calling: bool = True
    json_output: bool = True
    structured_output: bool = True
    vision: bool = False