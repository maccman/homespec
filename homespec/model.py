"""The core: a :class:`House` holds definitions and elements; compiling it realizes exact geometry into a :class:`Build`.

The core does not know what a wall is. An element is any ``@element`` class
that subclasses :class:`Element` and implements :meth:`Element.realize`. The
standard vocabulary in :mod:`homespec.elements` is one library of such
classes; a project may define its own.

Registration is implicit inside a ``with House(...)`` block, so a project
file reads as a list of declarations::

    with House("cabin") as house:
        L0 = Level("L0", height=2700)
        W1 = Wall("W1", (0, 0), (6000, 0), assembly=ext, level=L0)
        Window("N1", host=W1, width=1200, height=1000, sill=900, at=1500)
"""
from __future__ import annotations

import contextvars
import dataclasses
from collections import OrderedDict
from collections.abc import Callable, Iterable, Iterator
from typing import Annotated, Any, ClassVar, TypeVar, cast, dataclass_transform

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, TypeAdapter
from pydantic.dataclasses import dataclass as _pydantic_dataclass

from .geometry import Point, Point3

# --------------------------------------------------------------------------- declaring things
CONFIG = ConfigDict(extra="forbid", arbitrary_types_allowed=True, validate_assignment=True)
_MISSING: Any = dataclasses.MISSING
T = TypeVar("T")


def positional(*, default: Any = _MISSING, default_factory: Any = _MISSING, kw_only: bool = False) -> Any:
    """Mark a field as positional after the id: ``start: Point = positional()``."""
    kwargs: dict[str, Any] = {"kw_only": kw_only}
    if default is not _MISSING:
        kwargs["default"] = default
    if default_factory is not _MISSING:
        kwargs["default_factory"] = default_factory
    return dataclasses.field(**kwargs)


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, dataclasses.field, positional))
def element(cls: type[T]) -> type[T]:
    """Class decorator for elements.

    Makes a validated dataclass whose fields are keyword-only except the id
    and any field declared with :func:`positional`. Type checkers see the
    real signature, so ``Wall("W1", start, end, assembly=...)`` type-checks.
    """
    return cast(type[T], _pydantic_dataclass(config=CONFIG, kw_only=True)(cls))


@dataclass_transform(kw_only_default=True, field_specifiers=(Field, dataclasses.field, positional))
def definition(cls: type[T]) -> type[T]:
    """Class decorator for definitions. Identical to :func:`element`; the name says what the class is."""
    return cast(type[T], _pydantic_dataclass(config=CONFIG, kw_only=True)(cls))


def _to_id(value: Any) -> Any:
    if isinstance(value, str):
        return value
    ident = getattr(value, "id", None)
    return ident if isinstance(ident, str) else value


Ref = Annotated[str, BeforeValidator(_to_id)]
"""A reference to a definition or element: accepts the object or its id, stores the id."""

Positive = Annotated[float, Field(gt=0)]
NonNegative = Annotated[float, Field(ge=0)]
Outline = Annotated[list[Point], Field(min_length=3)]

_registration = contextvars.ContextVar("homespec_registration", default=True)
_adapters: dict[type, TypeAdapter[Any]] = {}


def dump(obj: Any, exclude: Iterable[str] = ()) -> dict[str, Any]:
    """A declaration as JSON-able data, references as ids."""
    adapter = _adapters.get(type(obj))
    if adapter is None:
        adapter = _adapters[type(obj)] = TypeAdapter(type(obj))
    return adapter.dump_python(obj, mode="json", exclude=set(exclude))


# --------------------------------------------------------------------------- small value types
class Relation(BaseModel):
    """A typed edge between two entities: ``subject --pred--> obj``. The subject is the entity that owns it."""

    pred: str
    obj: str


class Extrusion(BaseModel):
    """A rectangular extrusion placed in the world.

    The parametric form exporters prefer over meshes: an IFC wall or void is
    ``length`` along ``u``, ``thickness`` along ``n`` and ``height`` up from
    ``origin``.
    """

    origin: Point3
    u: Point
    n: Point
    length: float
    thickness: float
    height: float


# --------------------------------------------------------------------------- declarations
@element
class _Registered:
    """Base for anything that registers itself with the current :class:`House` on construction."""

    id: str = positional()

    def __post_init__(self) -> None:
        if _registration.get():
            house = House.current_or_none()
            if house is not None:
                house._register(self)


@element
class Definition(_Registered):
    """Something a house is described in terms of but that has no geometry of its own.

    Levels, assemblies, materials, the grid and the site are definitions.
    Subclasses name the :class:`House` attribute they live in via ``registry``.
    """

    registry: ClassVar[str]
    singleton: ClassVar[bool] = False


class Realized(BaseModel):
    """What :meth:`Element.realize` returns: geometry plus the facts derived while building it."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    solid: Any = None
    derived: dict[str, Any] = Field(default_factory=dict)
    relations: list[Relation] = Field(default_factory=list)
    extrusion: Extrusion | None = None
    material: str | None = None
    level: str | None = None
    tags: set[str] = Field(default_factory=set)


@element
class Element(_Registered):
    """Something that is realized into geometry and exported.

    Subclasses set ``kind`` (a short noun, also the entity's primary tag),
    ``ifc_class`` (or ``None`` to keep it out of the IFC) and ``physical``
    (``False`` for spaces and groups). They implement :meth:`realize`, and
    :meth:`deps` when they must be realized after another element.
    """

    kind: ClassVar[str] = "element"
    ifc_class: ClassVar[str | None] = "IfcBuildingElementProxy"
    physical: ClassVar[bool] = True

    tags: set[str] = dataclasses.field(default_factory=set)
    level: Ref | None = None
    material: Ref | None = None

    def deps(self) -> list[str]:
        """Ids this element must be realized after (its host wall, for an opening)."""
        return []

    def realize(self, ctx: Context) -> Realized:
        raise NotImplementedError(f"{type(self).__name__} does not implement realize()")

    def all_tags(self) -> set[str]:
        return {self.kind} | set(self.tags)


# --------------------------------------------------------------------------- the compiled house
class Built(BaseModel):
    """An element after realization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    element: Any
    solid: Any = None
    derived: dict[str, Any] = Field(default_factory=dict)
    relations: list[Relation] = Field(default_factory=list)
    extrusion: Extrusion | None = None
    material: str | None = None
    level: str | None = None
    tags: set[str] = Field(default_factory=set)

    @property
    def id(self) -> str:
        return self.element.id

    def has(self, *tags: str) -> bool:
        return all(t in self.tags for t in tags)

    def related(self, pred: str) -> list[str]:
        return [r.obj for r in self.relations if r.pred == pred]


M = TypeVar("M", bound=BaseModel)


class Build:
    """The compiled house: every entity, in realization order, with exact geometry."""

    def __init__(self, house: House) -> None:
        self.house = house
        self.entities: OrderedDict[str, Built] = OrderedDict()

    def add(self, element: Element, realized: Realized) -> Built:
        if element.id in self.entities:
            raise ValueError(f"duplicate entity id {element.id!r}")
        built = Built(
            element=element, solid=realized.solid, derived=realized.derived, relations=list(realized.relations),
            extrusion=realized.extrusion, material=realized.material or element.material, level=realized.level or element.level,
            tags=element.all_tags() | realized.tags,
        )
        self.entities[element.id] = built
        return built

    def relate(self, subject: str, pred: str, obj: str) -> None:
        self[subject].relations.append(Relation(pred=pred, obj=obj))

    def __getitem__(self, id: str) -> Built:
        try:
            return self.entities[id]
        except KeyError:
            raise KeyError(f"no entity {id!r} in build") from None

    def __iter__(self) -> Iterator[Built]:
        return iter(self.entities.values())

    def __len__(self) -> int:
        return len(self.entities)

    def tagged(self, *tags: str) -> list[Built]:
        return [b for b in self if b.has(*tags)]

    def write(self, out_dir: str) -> Any:
        """Write the IR (``ir.json`` plus geometry files) to ``out_dir``. Returns the :class:`homespec.ir.IRDocument`."""
        from .ir import write_ir

        return write_ir(self, out_dir)


class Context:
    """What an element sees while it is being realized."""

    def __init__(self, house: House, build: Build) -> None:
        self.house = house
        self.build = build
        self._pending: list[tuple[Element, Realized]] = []

    # ---- definitions
    def level(self, element_or_id: Element | str) -> Any:
        lid = element_or_id.level if isinstance(element_or_id, Element) else element_or_id
        if lid is None:
            raise ValueError(f"{getattr(element_or_id, 'id', element_or_id)!r} has no level")
        try:
            return self.house.levels[lid]
        except KeyError:
            raise KeyError(f"unknown level {lid!r}") from None

    def assembly(self, id: str) -> Any:
        try:
            return self.house.assemblies[id]
        except KeyError:
            raise KeyError(f"unknown assembly {id!r}") from None

    def material(self, id: str) -> Any:
        try:
            return self.house.materials[id]
        except KeyError:
            raise KeyError(f"unknown material {id!r}") from None

    # ---- other entities
    def built(self, id: str) -> Built:
        if id not in self.build.entities:
            raise KeyError(f"{id!r} is not realized yet; declare it in deps() to order after it")
        return self.build[id]

    def derived(self, id: str, model: type[M]) -> M:
        """The derived facts of an already-realized entity, as a typed model."""
        return model.model_validate(self.built(id).derived)

    def cut(self, id: str, void: Any) -> None:
        """Subtract a solid from an already-realized entity (an opening from its wall)."""
        b = self.built(id)
        b.solid = b.solid - void

    def emit(self, element: Element, realized: Realized) -> None:
        """Add a sub-entity produced while realizing another (glass in a window, beams in a ceiling). It lands right after its parent."""
        self._pending.append((element, realized))

    def relate(self, subject: str, pred: str, obj: str) -> None:
        self.build.relate(subject, pred, obj)


class House:
    """The registry a project file fills in. ``with House(name) as house:`` makes it current."""

    _stack: ClassVar[list[House]] = []

    def __init__(self, name: str, units: str = "mm") -> None:
        if units != "mm":
            raise ValueError("homespec works in millimetres; convert at the boundary with homespec.units")
        self.name = name
        self.units = units
        self.levels: dict[str, Any] = {}
        self.assemblies: dict[str, Any] = {}
        self.materials: dict[str, Any] = {}
        self.grid: Any = None
        self.site: Any = None
        self.elements: OrderedDict[str, Element] = OrderedDict()
        self.checks: list[Callable[..., Any]] = []

    # ---- context
    def __enter__(self) -> House:
        House._stack.append(self)
        return self

    def __exit__(self, *exc: Any) -> None:
        House._stack.pop()

    @classmethod
    def current(cls) -> House:
        if not cls._stack:
            raise RuntimeError("no active House: declare elements inside `with House(...) as house:` or pass them to house.add()")
        return cls._stack[-1]

    @classmethod
    def current_or_none(cls) -> House | None:
        return cls._stack[-1] if cls._stack else None

    # ---- registration
    def _register(self, obj: Any) -> None:
        if isinstance(obj, Definition):
            if obj.singleton:
                setattr(self, obj.registry, obj)
            else:
                registry: dict[str, Any] = getattr(self, obj.registry)
                if obj.id in registry:
                    raise ValueError(f"duplicate {type(obj).__name__} id {obj.id!r}")
                registry[obj.id] = obj
        elif isinstance(obj, Element):
            if obj.id in self.elements:
                raise ValueError(f"duplicate element id {obj.id!r}")
            self.elements[obj.id] = obj
        else:
            raise TypeError(f"cannot register {type(obj).__name__}")

    def add(self, *objs: Any) -> Any:
        """Register definitions or elements explicitly (the alternative to the ``with`` block)."""
        for o in objs:
            self._register(o)
        return objs[0] if len(objs) == 1 else objs

    def check(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator: a project-specific rule. ``fn(ir)`` yields :class:`homespec.checks.Result` or tuples."""
        self.checks.append(fn)
        return fn

    # ---- compile
    def compile(self) -> Build:
        """Realize every element, in dependency order, into a :class:`Build`."""
        build = Build(self)
        ctx = Context(self, build)
        token = _registration.set(False)
        try:
            for el in _ordered(self.elements):
                realized = el.realize(ctx)
                build.add(el, realized)
                for child, child_realized in ctx._pending:
                    build.add(child, child_realized)
                ctx._pending.clear()
        finally:
            _registration.reset(token)
        return build


def _ordered(elements: OrderedDict[str, Element]) -> list[Element]:
    """Declaration order, except that an element comes after everything in its ``deps()``."""
    remaining = list(elements.values())
    done: set[str] = set()
    out: list[Element] = []
    while remaining:
        progressed = False
        for el in list(remaining):
            deps = el.deps()
            for d in deps:
                if d not in elements:
                    raise KeyError(f"{el.id!r} depends on unknown element {d!r}")
            if all(d in done for d in deps):
                out.append(el)
                done.add(el.id)
                remaining.remove(el)
                progressed = True
        if not progressed:
            raise ValueError("dependency cycle among: " + ", ".join(e.id for e in remaining))
    return out
