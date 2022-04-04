#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    __init__.py
    ~~~~~~~~~~~

    A wrapper for the regex library for advanced regex pattern management

    :copyright: (c) 2022 by Biagio Distefano.
    :license: MIT
"""

__title__ = 'replus'
__version__ = '0.2.0'
__author__ = 'Biagio Distefano'


import json
import os
from pathlib import Path
from typing import List, Tuple, Union
from collections import Counter
from collections import defaultdict

import regex

from .exceptions import NoSuchGroup, UnknownTemplateGroup, RepeatedSpecialGroup


class Replus:

    """
    The Replus engine class builds and compiles regular expressions based on templates.

    :ivar group_counter: a Counter object to count group name occurance on each template
    :ivar patterns: a list of tuples made of [(key, pattern, template), ...]
    :ivar patterns_src: a dict containing all of patterns_dir/\*.json combined together, "patterns" excluded
    :ivar patterns_all: all patterns that can be run, e.g. {"dates": [pattern0, pattern1], ...}
    :ivar all_groups: a dict of list with the templates as keys, e.g. {pattern_template_a: [group_0, group_1], pattern_template_b: [group_0, group_1]}
    """

    group_pattern = r"{{((?P<special>#|\?[:>!=]|\?[aimsxl]:|\?<[!=])?(?P<key>[\w_]+)(@(?P<index>\d+))?)}}"  # regex used to match the groups' placeholder

    def __init__(self, patterns_dir: os.PathLike, whitespace_noise: str = None, flags: int = regex.V0):
        """
        Instanciates the Replus engine

        :param patterns_dir: the path to the directory where the \*.json pattern templates are stored
        :type patterns_dir: os.PathLike

        :param whitespace_noise: a pattern to replace white space in the template
        :type whitespace_noise: str, defaults to None

        :param flags: the regex flags to compile the patterns
        :type flags: int, defaults to regex.V0
        """

        self.group_counter = Counter()
        self.patterns = []
        self.patterns_src = {}
        self.patterns_all = {}
        self.all_groups = defaultdict(list)
        self.patterns_src, self.patterns_all = self._load_models(patterns_dir)
        self._build_patterns()

        if whitespace_noise is not None:
            self.patterns = [(k, regex.compile(regex.sub(r" +|\\\s+", f"({whitespace_noise})", p), flags=flags), t)
                             for k, p, t in self.patterns]
        else:
            self.patterns = [(k, regex.compile(p, flags=flags), t) for k, p, t in self.patterns]

    def parse(self, string: str, *filters, exclude: List = None, overlap: bool = False):
        """
        Returns a list of Match objects

        :param string: the string to parse
        :type string: str

        :param filters: one or more pattern types to parse; if none is provided, all will be used
        :type filters: Tuple[str]

        :param exclude: a list of pattern types to exclude
        :type exclude: List[str], defaults to None

        :param overlap: if True will allow overlapping matches
        :type overlap: bool, defaults to False

        :return: a list of Match objects
        :rtype: List[Match]
        """

        exclude = exclude or []
        matches = []
        for k, pattern, template in self.patterns:
            if filters and k not in filters or (k in exclude):
                continue
            for m in regex.finditer(pattern, string):
                match = Match(k, m, self.all_groups[template], pattern)
                matches.append(match)
        if not overlap:
            return self.purge_overlaps(matches)
        matches.sort(key=lambda x: x._start)
        return matches

    def search(self, string: str, *filters, exclude: list = None, allow_overlap: bool = False) -> "Match":
        """
        Returns a single Match object

        :param string: the string to parse
        :type string: str

        :param filters: one or more pattern types to parse; if none is provided, all will be used
        :type filters: Tuple[str]

        :param exclude: a list of pattern types to exclude
        :type exclude: List[str], defaults to None

        :param overlap: if True will allow overlapping matches
        :type overlap: bool, defaults to False

        :return: a Match object
        :rtype: Match
        """

        for m in self.parse(string, *filters, exclude=exclude, overlap=allow_overlap):
            return m
        return None

    def _build_patterns(self):
        for key, patterns in self.patterns_all.items():
            for pattern in patterns:
                self.group_counter = Counter()
                try:
                    self.patterns.append((key, self._build_pattern(pattern, pattern), pattern))
                except Exception as e:
                    raise Exception(e, f"Fatal error building patterns in file '{key}.json'")

    def _build_pattern(self, pattern: str, template: str):
        for group_match in regex.finditer(self.group_pattern, pattern):
            return self._build_pattern(self._build_group(group_match, pattern, template), template)
        return pattern

    def _build_group(self, group_match: regex.regex.Match, pattern: str, template: str):
        group_key = group_match.group("key")
        special = group_match.group("special")
        alts = self.patterns_src.get(group_key)
        if alts is not None:
            group_count = self.group_counter[group_key]
            if special is None:
                new_pattern = pattern.replace(
                    f"{{{{{group_key}}}}}",
                    f"(?P<{group_key}_{group_count}>{self._pipe_together(alts)})",
                    1
                )
                self.all_groups[template].append(f"{group_key}_{group_count}")
                self.group_counter[group_key] += 1
            else:
                if special == "#":
                    back_reference_index = int(group_match.group("index")) if group_match.group("index") else 1
                    assert group_count >= back_reference_index, f"Attempting to reference non-existing group: " \
                                                                f"{group_key}_{group_count - back_reference_index}"
                    new_pattern = pattern.replace(
                        f"{{{{{group_match.group(1)}}}}}",
                        f"(?P={group_key}_{group_count - back_reference_index})",
                        1
                    )
                else:
                    new_pattern = pattern.replace(
                        f"{{{{{special+group_key}}}}}",
                        f"({special}{self._pipe_together(alts)})",
                        1
                    )
                    self.group_counter[group_key] += 1
        else:
            if special:
                raise RepeatedSpecialGroup(f"Repeated special group for {group_key}: '{special}'")
            for sk in ["?:", "?>", "?!", "?=", "?<=", "?<!", "?a:", "?i:", "?m:", "?s:", "?x:", "?l:"]:
                alts = self.patterns_src.get(f"{sk}{group_key}")
                if alts is not None:
                    new_pattern = pattern.replace(
                        f"{{{{{group_key}}}}}",
                        f"({sk}{self._pipe_together(alts)})"
                    )
                    assert new_pattern != pattern, f"Could not build pattern '{group_key}'"
                    return new_pattern
            raise UnknownTemplateGroup(group_key)
        return new_pattern

    @staticmethod
    def _pipe_together(alts):
        return "|".join(alts)

    @staticmethod
    def purge_overlaps(matches: Union[List["Match"], List["Group"]]) -> Union[List["Match"], List["Group"]]:
        """
        Purge the list of Match and Group objects from overlapping instances

        :param matches: a list of Match or Group objects
        :type matches: Union[List[Match], List[Group]]

        :retrurn: a list of Match or Group objects
        :rtype: Union[List[Match], List[Group]]
        """

        matches.sort(key=lambda x: x._start)
        purged = []
        if len(matches) <= 1:
            return matches
        purged.append(matches[0])
        for m in matches[1:]:
            if m._start >= purged[-1]._end:
                purged.append(m)
            else:
                if m._end >= purged[-1]._end:
                    if m.length > purged[-1].length:
                        purged.pop()
                        purged.append(m)
        return purged

    @staticmethod
    def _load_models(patterns_dir: os.PathLike) -> Tuple[dict]:
        patterns_dir = Path(patterns_dir).absolute()
        patterns_src = {}
        patterns_all = {}
        loaded = {}
        for pattern_filepath in patterns_dir.iterdir():
            if not (pattern_filepath.is_file() and pattern_filepath.suffix == ".json"):
                continue
            patterns_name = pattern_filepath.stem
            with pattern_filepath.open("r") as f:
                config_obj = json.load(f)
                if run_patterns := config_obj.pop("$PATTERNS", None):
                    patterns_all[patterns_name] = run_patterns
                for k in config_obj:
                    if k in loaded:
                        raise KeyError(
                            f"Duplicated pattern name \"{k}\" in {str(pattern_filepath)} "
                            f"already loaded from {loaded[k]}"
                        )
                    else:
                        loaded[k] = str(pattern_filepath)
                patterns_src.update(config_obj)
        return patterns_src, patterns_all


class Match:

    """
    A Match object is an abstract and expanded representation of a regex.regex.Match

    :ivar type: the type of the match, corresponding to the stem of the file of the pattern's template
    :ivar match: a regex.regex.Match object
    :ivar value: the string value of the match
    :ivar offset: the offset of the match ``{"start": int, "end": int}``
    :ivar pattern: the string representation of the pattern that matched
    :ivar lenth: the length of the match (no. of characters)
    :ivar all_group_names: all the names of all the groups for the corresponding pattern for this match
    :ivar _start: the start offset of the Match
    :ivar _end: the end offset Match
    :ivar _span: the span of the Match (_start, _end)
    """

    def __init__(self, match_type: str, match: regex.regex.Match, all_groups_names: List[str], pattern: regex.regex.Pattern):
        """
        Instanciates a Match object

        :param match_type: the type of the match, corresponding to the stem of the file of the pattern's template
        :type match_type: str

        :param match: a regex.regex.Match object
        :type match: regex.regex.Match

        :param all_groups_names: all the names of all the groups for the corresponding pattern for this match
        :type all_group_names: List[str]

        :param pattern: the pattern that matched
        :type: pattern: regex.regex.Pattern
        """

        self.type = match_type
        self.match = match
        self.value = match.group()
        self.offset = {"start": self.start(), "end": self.end()}
        self.pattern = pattern.pattern
        self.length = self.end() - self.start()
        self.all_group_names = all_groups_names
        self._start = self.start()
        self._end = self.end()
        self._span = self.span()

    def start(self, group_name: str = None, rep_index: int = 0) -> int:
        """
        Returns the start character index of self or of Group with group_name
        
        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the start index of the Match
        :rtype: int
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.start(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.start()
    
    def end(self, group_name: str = None, rep_index: int = 0) -> int:
        """
        Returns the end character index of self or of Group with group_name
        
        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the end index of the Match
        :rtype: int
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.end(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.end()

    def span(self, group_name: str = None, rep_index: int = 0) -> Tuple[int]:
        """
        Returns the span of self or of Group with group_name

        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the span of the Match
        :rtype: Tuple[int]
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.span(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.span()

    def groups(self, group_query: str = None, root: bool = False) -> List["Group"]:
        """
        Returns a list of repeated Group objects that belong to the Match object
        
        :param group_query: the name of the group to find repetitions of
        :type group_query: str, defaults to None

        :param root: includes the root if True
        :type root: bool, defaults to False

        :return: a list of Group objects
        :rtype: List[Group]
        """

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
                            if self._start <= start and end <= self._end:
                                groups.append(Group(self.match, group_i, self, rep_index=j))
                except IndexError:
                    break
                if group_query is None:
                    break
                i += 1
        if root:
            return Replus.purge_overlaps(groups)
        return groups

    def group(self, group_name: str) -> Union["Group", None]:
        """
        Returns a Group object with the given group_name or None

        :param group_name: the name of the group
        :type group_name: str

        :return: a Group object
        :rtype: Union[Group, None]
        """

        for group in self.groups(group_name):
            return group
        return None

    def first(self) -> Union["Group", None]:
        """
        Returns the first Group object or None

        :return: the first Group object
        :rtype: Union[Group, None]
        """

        for group in self.groups():
            return group
        return None

    def last(self) -> Union["Group", None]:
        """
        Returns the last Group object or None

        :return: the last Group object
        :rtype: Union[Group, None]
        """

        for group in reversed(self.groups()):
            return group
        return None

    def serialize(self) -> dict:
        """
        Returns a dict representation of the Match object structured as follows:

        .. code-block::

            {
                "type": self.type,
                "offset": self.offset,
                "value": self.value,
                "groups": [<serialized_groups>, ], # <- including root (itself)
            }

        :return: a dict representation of the Match object
        :rtype: dict
        """

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

    def json(self, *args, **kwargs) -> str:
        """
        Returns a json-string of the serialized object

        :return: a json-string of the serialized object
        :rtype: str
        """

        return json.dumps(self.serialize(), *args, **kwargs)
    
    def __repr__(self) -> str:
        return f"<[Match {self.type}] span{self._span}: {self.value}>"

    
class Group:

    """
    A Group object is an abstract and expanded representation of a regex.regex.Match

    :ivar root: the root Match object
    :ivar match: a regex.regex.Match object
    :ivar name: the name of the group, including its rep_index. E.g.: date_0
    :ivar key: the key of the group, i.e. the name without the rep_index
    :ivar value: the string value of the match
    :ivar offset: the offset of the match ``{"start": int, "end": int}``
    :ivar length: the length of the match (no. of characters)
    :ivar rep_index: the repetition index
    :ivar _start: the start offset of the Match
    :ivar _end: the end offset Match
    :ivar _span: the span of the Match (_start, _end)
    """

    def __init__(self, match: regex.regex.Match, group_name: str, root: Match, rep_index: int = 0):
        self.root = root
        self.match = match
        self.name = group_name
        self.key = regex.sub(r"_\d+$", r"", self.name)
        self.value = match.captures(group_name)[rep_index]
        self.offset = {"start": self.start(), "end": self.end()}
        self.length = self.end() - self.start()
        self.rep_index = rep_index
        self._start = self.start()
        self._end = self.end()
        self._span = self.span()

    def start(self, group_name: str = None, rep_index: int = 0) -> int:
        """
        Returns the start character index of self or of Group with group_name
        
        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the start index of the Match
        :rtype: int
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.start(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.starts(self.name)[rep_index]
    
    def end(self, group_name: str = None, rep_index: int = 0) -> int:
        """
        Returns the end character index of self or of Group with group_name
        
        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the end index of the Match
        :rtype: int
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.end(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.ends(self.name)[rep_index]

    def span(self, group_name: str = None, rep_index: int = 0) -> Tuple[int]:
        """
        Returns the span of self or of Group with group_name

        :param group_name: the name of the group
        :type group_name: str, defaults to None

        :param rep_index: the repetition index of the group
        :type rep_index: int, defaults to 0

        :return: the span of the Match
        :rtype: Tuple[int]
        """

        if group_name is not None:
            if group := self.group(group_name):
                return group.span(rep_index=rep_index)
            raise NoSuchGroup
        return self.match.spans(self.name)[rep_index]

    def groups(self, group_query: str = None, root = False) -> List["Group"]:
        """
        Returns a list of repeated Group objects that belong to the Group object
        
        :param group_query: the name of the group to find repetitions of
        :type group_query: str, defaults to None

        :param root: includes the root if True
        :type root: bool, defaults to False

        :return: a list of Group objects
        :rtype: List[Group]
        """

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
                                if self._start <= start and end <= self._end:
                                    groups.append(self.__class__(self.match, group_i, self.root, rep_index=j))
                    except IndexError:
                        break
                if group_query is None:
                    break
                i += 1
        groups.sort(key=lambda x: x._start)
        if root:
            return Replus.purge_overlaps(groups)
        return groups

    def group(self, group_name) -> "Group":
        """
        Returns a Group object with the given group_name or None

        :param group_name: the name of the group
        :type group_name: str

        :return: a Group object
        :rtype: Union[Group, None]
        """

        for group in self.groups(group_name):
            return group
        return None

    def first(self) -> Union["Group", None]:
        """
        Returns the first Group object or None

        :return: the first Group object
        :rtype: Union[Group, None]
        """

        for group in self.groups():
            return group
        return None

    def last(self) -> Union["Group", None]:
        """
        Returns the last Group object or None

        :return: the last Group object
        :rtype: Union[Group, None]
        """

        for group in reversed(self.groups()):
            return group
        return None

    def serialize(self) -> dict:
        """
        Returns a dict representation of the Match object structured as follows

        .. code-block::

            o = {
                "key": self.key,
                "name": self.name,
                "offset": self.offset,
                "value": self.value,
                "groups": {subgroup_0: [group_object.serialize()]}
            }

        :return: a dict representation of the Match object
        :rtype: dict
        """

        o = {
            "key": self.key,
            "name": self.name,
            "offset": self.offset,
            "value": self.value,
            "groups": defaultdict(list)
        }
        for g in self.groups(root=True):
            o["groups"][g.key].append(g.serialize())
        o["groups"] = dict(o["groups"])
        return o

    def json(self, *args, **kwargs) -> str:
        """
        Returns a json-string of the serialized object

        :return: a json-string of the serialized object
        :rtype: str
        """

        return json.dumps(self.serialize(), *args, **kwargs)

    def reps(self) -> List["Group"]:
        """
        Returns a list of the Group object's repetitions

        :return: a a list of the Group object's repetitions
        :rtype: List[Group]
        """

        if len(self.match.starts(self.name)) > 1:
            return [
                self.__class__(self.match, self.name, self.root, rep_index=i)
                for i in range(len(self.match.starts(self.name)))
            ]
        return []

    def __repr__(self) -> str:
        return f"<Group {self.name} span{self._span} @{self.rep_index}: '{self.value}'>"
