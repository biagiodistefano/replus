import json
from collections import Counter
from collections import defaultdict

import regex

from .helpers import FLAG_MAP
from .helpers import load_models


class Engine:
    GROUP_PATTERN = r"{{((?P<special>#|\?[:>!=]|\?<[!=])?(?P<key>[\w_]+)(@(?P<index>\d+))?)}}"

    def __init__(self, model: str, *flags, ws_noise: str = None):

        self.group_counter = Counter()  # counter object to count group name occurance on each template
        self.patterns = []  # will be a list of tuples [(key, pattern, template)]
        self.patterns_src = {}  # a giant dict containing all of models/*.json combined together, "patterns" excluded
        self.patterns_all = {}  # all "patterns", e.g. { "judicial_references": [pattern0, pattern1], ... }
        self.all_groups = defaultdict(list)  # { pattern_template_A: [my_group_0, my_group_1 ...], ...}

        _flags = 0
        for f in flags:
            _flags |= FLAG_MAP[f]
        self.__load_models(model)
        self.__build_patterns()
        # self.patterns.sort(key=lambda x: len(x[1]), reverse=True)
        if ws_noise is not None:
            self.patterns = [(k, regex.compile(regex.sub(r" |\\\s", f"({ws_noise})", p), _flags), t)
                             for k, p, t in self.patterns]
        else:
            self.patterns = [(k, regex.compile(p, _flags), t) for k, p, t in self.patterns]

    def parse(self, string: str, *filters, exclude: list = None, allow_overlap: bool = False):
        """Return a list of Match objects
        :param string: The string to parse
        :param filters: one or more pattern types to parse; if none is provided, all will be used
        :param exclude: a list of pattern types to exclude
        :param allow_overlap: if False (default) will purge overlapping matches
        :return: A list of Match objects
        """
        matches = []
        filters = set(filters)
        if exclude is None:
            exclude = set()
        else:
            exclude = set(exclude)
        for k, pattern, template in self.patterns:
            if (len(filters) and k not in filters) or (k in exclude):
                continue
            for m in regex.finditer(pattern, string):
                match = self.Match(k, m, self.all_groups[template], pattern)
                matches.append(match)
        if not allow_overlap:
            return self.purge_overlaps(matches)
        matches.sort(key=lambda x: x.start)
        return matches

    def search(self, string: str, *filters, exclude: list = [], allow_overlap: bool = False):
        for m in self.parse(string, *filters, exclude=exclude, allow_overlap=allow_overlap):
            return m
        return None

    def __build_patterns(self):
        for key, patterns in self.patterns_all.items():
            for pattern in patterns:
                self.group_counter = Counter()
                try:
                    self.patterns.append((key, self.__build_pattern(pattern, pattern), pattern))
                except Exception as e:
                    raise Exception(e, f"Fatal error building patterns in file '{key}.json'")

    def __build_pattern(self, pattern, template):
        for group_match in regex.finditer(self.GROUP_PATTERN, pattern):
            return self.__build_pattern(self.__build_group(group_match, pattern, template), template)
        return pattern

    def __build_group(self, group_match, pattern, template):
        group_key = group_match.group("key")
        special = group_match.group("special")
        alts = self.patterns_src.get(group_key)
        if alts is not None:
            group_count = self.group_counter[group_key]
            if special is None:
                new_pattern = pattern.replace(
                    f"{{{{{group_key}}}}}",
                    f"(?P<{group_key}_{group_count}>{self.__build_alts(alts)})",
                    1
                )
                self.all_groups[template].append(f"{group_key}_{group_count}")
                self.group_counter[group_key] += 1
            else:
                if special == "#":
                    back_reference_index = int(group_match.group("index")) if group_match.group("index") else 1
                    assert group_count >= back_reference_index, f"Attempting to reference unexisting group: " \
                                                                f"{group_count - back_reference_index}"
                    new_pattern = pattern.replace(
                        f"{{{{{group_match.group(1)}}}}}",
                        f"(?P={group_key}_{group_count - back_reference_index})",
                        1
                    )
                else:
                    new_pattern = pattern.replace(
                        f"{{{{{special + group_key}}}}}",
                        f"({special}{self.__build_alts(alts)})",
                        1
                    )
                    self.group_counter[group_key] += 1
        else:
            if special:
                raise self.Exceptions.RepeatedSpecialGroup(f"Repeated special group for {group_key}: '{special}'")
            for sk in ["?:", "?>", "?!", "?=", "?<=", "?<!"]:
                alts = self.patterns_src.get(f"{sk}{group_key}")
                if alts is not None:
                    new_pattern = pattern.replace(
                        f"{{{{{group_key}}}}}",
                        f"({sk}{self.__build_alts(alts)})"
                    )
                    assert new_pattern != pattern, f"Could not build pattern '{group_key}'"
                    return new_pattern
            raise self.Exceptions.UnknownTemplateGroup(group_key)
        return new_pattern

    @staticmethod
    def __build_alts(alts):
        return "|".join(alts)

    def __load_models(self, model):
        self.patterns_src, self.patterns_all = load_models(model)

    @classmethod
    def purge_overlaps(cls, matches):
        matches.sort(key=lambda x: x.start)
        purged = []
        if len(matches) > 1:
            purged.append(matches[0])
            for m in matches[1:]:
                if m.start >= purged[-1].end:
                    purged.append(m)
                else:
                    if m.end >= purged[-1].end:
                        if m.length > purged[-1].length:
                            purged.pop()
                            purged.append(m)
        else:
            return matches
        return purged

    class Match:

        def __init__(self, match_type, match, all_groups_names, pattern):
            self.type = match_type
            self.match = match
            self.start = match.start()
            self.end = match.end()
            self.span = match.span()
            self.offset = {"start": self.start, "end": self.end}
            self.re = pattern.pattern
            self.value = match.group()
            self.length = self.end - self.start
            self.all_group_names = all_groups_names

        def groups(self, group_query=None, root=False):
            groups = []
            all_groups = [group_query] if group_query is not None else self.all_group_names
            for group_name in all_groups:
                i = 0
                group_i = group_name
                while True:
                    if group_query is not None:
                        group_i = f"{group_name}_{i}"
                    try:
                        g = self.match.group(group_i)
                        if g is not None:
                            for j, (start, end) in enumerate(self.match.spans(group_i)):
                                if self.start <= start and end <= self.end:
                                    groups.append(self.Group(self.match, group_i, self, rep_index=j))
                    except IndexError:
                        break
                    if group_query is None:
                        break
                    i += 1
            if root:
                return Engine.purge_overlaps(groups)
            return groups

        def group(self, group_name):
            groups = self.groups(group_name)
            if len(groups):
                return groups[0]
            else:
                return None

        def serialize(self):
            o = {
                "type": self.type,
                "offset": self.offset,
                "value": self.value,
                "groups": defaultdict(list),
            }
            for g in self.groups(root=True):
                o["groups"][g.key].append(g.serialize())
            o["groups"] = dict(o["groups"])
            return o

        def first(self):
            try:
                return self.groups()[0]
            except IndexError:
                return None

        def last(self):
            try:
                return self.groups()[-1]
            except IndexError:
                return None

        @property
        def json(self):
            return json.dumps(self.serialize(), indent=2)

        def __repr__(self):
            return f"<[Match {self.type}] span{self.span}: {self.value}>"

        class Group:
            def __init__(self, match, group_name, root, rep_index=0):
                self.root = root
                self.match = match
                self.start = match.starts(group_name)[rep_index]
                self.end = match.ends(group_name)[rep_index]
                self.span = match.spans(group_name)[rep_index]
                self.offset = {"start": self.start, "end": self.end}
                self.value = match.captures(group_name)[rep_index]
                self.name = group_name
                self.length = self.end - self.start
                self.key = regex.sub(r"_\d+$", r"", self.name)
                self.rep_index = rep_index
                self.__parent = None

            def groups(self, group_query=None, root=False):
                def is_next(g1, g2):
                    return self.root.all_group_names.index(g1) > self.root.all_group_names.index(g2)

                groups = []
                all_groups = [group_query] if group_query is not None else self.root.all_group_names
                for group_name in all_groups:
                    i = 0
                    group_i = group_name
                    while True:
                        if group_query is not None:
                            group_i = f"{group_name}_{i}"
                        if self.name != group_i:  # doesn't return itself, just its children
                            try:
                                g = self.match.group(group_i)
                                if g is not None and is_next(group_i, self.name):  # returning just its children
                                    for j, (start, end) in enumerate(self.match.spans(group_i)):
                                        if self.start <= start and end <= self.end:
                                            groups.append(
                                                self.__class__(self.match, group_i, self.root, rep_index=j)
                                            )
                            except IndexError:
                                break
                        if group_query is None:
                            break
                        i += 1
                groups.sort(key=lambda x: x.start)
                if root:
                    return Engine.purge_overlaps(groups)
                return groups

            def group(self, group_name):
                groups = self.groups(group_query=group_name)
                if len(groups):
                    return groups[0]
                else:
                    return None

            def first(self):
                try:
                    return self.groups()[0]
                except IndexError:
                    return None

            def last(self):
                try:
                    return self.groups()[-1]
                except IndexError:
                    return None

            def serialize(self):
                o = {
                    "offset": self.offset,
                    "value": self.value,
                    "name": self.name,
                    "groups": defaultdict(list)
                }
                for g in self.groups(root=True):
                    o["groups"][g.key].append(g.serialize())
                o["groups"] = dict(o["groups"])
                return o

            @property
            def json(self):
                return json.dumps(self.serialize(), indent=2)

            @property
            def parent(self):
                if self.__parent:
                    return self.__parent
                for g in reversed(self.root.groups()):
                    if g.name == self.name:
                        continue
                    if g.start <= self.start and self.end <= g.end:
                        self.__parent = g
                        return g
                return self.root

            def reps(self):
                if len(self.match.starts(self.name)) > 1:
                    return [
                        self.__class__(self.match, self.name, self.root, rep_index=i)
                        for i in range(len(self.match.starts(self.name)))
                    ]
                return []

            def __repr__(self):
                return f"<Group {self.name} span{self.span} @{self.rep_index}: '{self.value}'>"

    class Exceptions:

        class UnknownTemplateGroup(Exception):
            pass

        class RepeatedSpecialGroup(Exception):
            pass
