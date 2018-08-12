import inspect
import warnings


def importer_is_main(depth, ignore_pkgs: tuple = None):
    if ignore_pkgs is None:
        ignore_pkgs = ('importlib', 'pkg_resources')
    try:
        importer_names = (
            n for n in map(try_name, inspect.stack()[1:])
            if not n.startswith(ignore_pkgs)
            )
    except TypeError:  # if inspect.stack() doesn't exist
        warnings.warn(
            "You are using a stackless Python implementation, so `require_main' is unavailable.",
            RuntimeWarning,
            stacklevel=2
            )
        return True
    
    # Add 1 because this function adds an additional stack frame on top
    # top of the requested depth (whose module.__name__ is 'ergo.core')
    for _ in range(1 + int(depth)):
        try:
            name = next(importer_names)
        except StopIteration:
            break
    return name == '__main__'


def try_name(frame_info):
    if '__name__' in frame_info.frame.f_globals:
        return frame_info.frame.f_globals['__name__']
    warnings.warn(
        "`require_main' may not function as intended, because"
        'a stack frame {!r} was encountered whose module appears'
        "to have no `__name__' associated with it.".format(frame_info),
        RuntimeWarning,
        stacklevel=3
        )
    # This would be None, but caller uses str.startswith
    return ''
