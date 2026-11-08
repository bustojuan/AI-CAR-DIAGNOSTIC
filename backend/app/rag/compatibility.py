from sqlalchemy import func, or_

FIELDS = ("manufacturer", "model", "engine", "engine_code", "transmission")
RELATED_VW_MODELS = ("golf", "golf plus", "jetta", "passat", "touran", "tiguan")
# Golf IV/Jetta-era documents may be used as explicit learning references too.
RELATED_VW_SOURCE_YEAR_START = 1999
RELATED_VW_SOURCE_YEAR_END = 2018


def same_tdi_family(metadata, vehicle):
    return all(
        (getattr(item, "engine", None) or "").strip().casefold() == "2.0 tdi"
        for item in (metadata, vehicle)
    )


def related_volkswagen(metadata, vehicle):
    """Learning references share a marque/era; this does not establish part fitment."""
    return (
        (vehicle.manufacturer or "").strip().casefold() == "volkswagen"
        and vehicle.model.strip().casefold() == "golf plus"
        and 2004 <= vehicle.model_year <= 2014
        and (metadata.manufacturer or "").strip().casefold() == "volkswagen"
        and (metadata.model or "").strip().casefold() in RELATED_VW_MODELS
        and metadata.model_year_start is not None
        and metadata.model_year_start <= RELATED_VW_SOURCE_YEAR_END
        and (
            metadata.model_year_end is None
            or metadata.model_year_end >= RELATED_VW_SOURCE_YEAR_START
        )
        and all(
            getattr(metadata, key, None) is None
            or (key == "engine_code" and same_tdi_family(metadata, vehicle))
            or (
                getattr(vehicle, key, None) is not None
                and getattr(metadata, key).strip().casefold()
                == getattr(vehicle, key).strip().casefold()
            )
            for key in ("engine", "engine_code", "transmission")
        )
    )


def related_volkswagen_predicates(document, vehicle):
    if (
        (vehicle.manufacturer or "").strip().casefold() != "volkswagen"
        or vehicle.model.strip().casefold() != "golf plus"
        or not 2004 <= vehicle.model_year <= 2014
    ):
        return [False]
    predicates = [
        func.lower(func.trim(document.manufacturer)) == "volkswagen",
        func.lower(func.trim(document.model)).in_(RELATED_VW_MODELS),
        document.model_year_start <= RELATED_VW_SOURCE_YEAR_END,
        or_(
            document.model_year_end.is_(None),
            document.model_year_end >= RELATED_VW_SOURCE_YEAR_START,
        ),
    ]
    for key in ("engine", "engine_code", "transmission"):
        column, actual = getattr(document, key), getattr(vehicle, key)
        matching = (
            column.is_(None)
            if actual is None
            else or_(column.is_(None), func.lower(func.trim(column)) == actual.strip().casefold())
        )
        if key == "engine_code" and (vehicle.engine or "").strip().casefold() == "2.0 tdi":
            matching = or_(matching, func.lower(func.trim(document.engine)) == "2.0 tdi")
        predicates.append(matching)
    return predicates


def compatible(metadata, vehicle):
    for key in FIELDS:
        expected = getattr(metadata, key, None)
        actual = getattr(vehicle, key, None)
        if expected is not None and (
            actual is None or expected.strip().casefold() != actual.strip().casefold()
        ):
            return False
    start, end = metadata.model_year_start, metadata.model_year_end
    return (start is None or vehicle.model_year >= start) and (
        end is None or vehicle.model_year <= end
    )


def vehicle_predicates(document, vehicle, *, skip_engine_code=False):
    predicates = []
    for key in FIELDS:
        if key == "engine_code" and skip_engine_code:
            continue
        column, actual = getattr(document, key), getattr(vehicle, key)
        predicates.append(
            column.is_(None)
            if actual is None
            else or_(column.is_(None), func.lower(func.trim(column)) == actual.strip().casefold())
        )
    predicates.extend(
        [
            or_(
                document.model_year_start.is_(None), document.model_year_start <= vehicle.model_year
            ),
            or_(document.model_year_end.is_(None), document.model_year_end >= vehicle.model_year),
        ]
    )
    return predicates
