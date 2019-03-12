import json
import os
import re

FLAG_MAP = {
    "i": re.IGNORECASE,
    "l": re.LOCALE,
    "m": re.MULTILINE,
    "s": re.S,
    "u": re.UNICODE,
    "x": re.X
}


def load_models(models_dir):
    patterns_src = {}
    patterns_all = {}
    loaded = {}
    for config_file in os.listdir(models_dir):
        if not config_file.endswith(".json"):
            continue
        config_filepath = os.path.join(models_dir, config_file)
        patterns_name = config_file.replace(".json", "")
        with open(config_filepath, "r") as f:
            config_obj = json.load(f)
            config_patterns = config_obj.pop("patterns", None)
            if config_patterns:
                patterns_all[patterns_name] = config_patterns
            for k in config_obj:
                if k in loaded:
                    print(f"WARNING: Duplicated pattern name \"{k}\" in {config_filepath} "
                          f"already loaded from {loaded[k]}")
                else:
                    loaded[k] = config_filepath
            patterns_src.update(config_obj)
    return patterns_src, patterns_all


def snake_case_toCamelCase(string):
    words = string.split("_")
    if len(words) == 1:
        return string.lower()
    return "".join([words[0].lower()] + [word.title() for word in words[1:]])


def camelCase_to_snake_case(string):
    s1 = re.sub(r'(\w)([A-Z][a-z]+)', r'\1_\2', string)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
