

class ReplusException(Exception):
    pass


class UnknownTemplateGroup(ReplusException):
    pass


class RepeatedSpecialGroup(ReplusException):
    pass


class NoSuchGroup(ReplusException):
    pass


class PatternBuildException(ReplusException):
    pass
