import json
import os

import regex

FLAG_MAP = {
    "i": regex.IGNORECASE,
    "l": regex.LOCALE,
    "m": regex.MULTILINE,
    "s": regex.S,
    "u": regex.UNICODE,
    "x": regex.X
}


def load_models(models_dir):
    patterns_src = {}
    patterns_all = {}
    loaded = {}
    for pattern_file in os.listdir(models_dir):
        if not pattern_file.endswith(".json"):
            continue
        pattern_filepath = os.path.join(models_dir, pattern_file)
        patterns_name = pattern_file.replace(".json", "")
        with open(pattern_filepath, "r") as f:
            config_obj = json.load(f)
            config_patterns = config_obj.pop("patterns", None)
            if config_patterns:
                patterns_all[patterns_name] = config_patterns
            for k in config_obj:
                if k in loaded:
                    print(f"WARNING: Duplicated pattern name \"{k}\" in {pattern_filepath} "
                          f"already loaded from {loaded[k]}")
                else:
                    loaded[k] = pattern_filepath
            patterns_src.update(config_obj)
    return patterns_src, patterns_all


def snake_case_to_camel_case(string):
    words = string.split("_")
    if len(words) == 1:
        return string.lower()
    return "".join([words[0].lower()] + [word.title() for word in words[1:]])


def camel_case_to_snake_case(string):
    s1 = regex.sub(r'(\w)([A-Z][a-z]+)', r'\1_\2', string)
    return regex.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
