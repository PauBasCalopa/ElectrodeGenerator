"""
Shared FEMM electrostatic model-building logic with pluggable backends.

The ``FEMMModelBuilder`` contains all model-construction steps (problem
setup, materials, boundaries, electrodes, outer box, dielectric label).
A backend strategy determines whether the commands are executed via
pyfemm COM calls (``ComBackend``) or collected as Lua script lines
(``LuaBackend``).

This eliminates the duplication that previously existed between the
live simulator and the Lua exporter.
"""

from abc import ABC, abstractmethod


# ------------------------------------------------------------------
# Backend interface
# ------------------------------------------------------------------
class FEMMBackend(ABC):
    """Abstract backend for emitting FEMM electrostatic commands."""

    @abstractmethod
    def newdocument(self, doctype): ...

    @abstractmethod
    def ei_probdef(self, units, prob_type, precision, depth, min_angle): ...

    @abstractmethod
    def ei_addmaterial(self, name, ex, ey, qv): ...

    @abstractmethod
    def ei_addboundprop(self, name, vs, qs, c0, c1, fmt): ...

    @abstractmethod
    def ei_addnode(self, x, y): ...

    @abstractmethod
    def ei_addsegment(self, x1, y1, x2, y2): ...

    @abstractmethod
    def ei_addarc(self, x1, y1, x2, y2, angle, maxseg): ...

    @abstractmethod
    def ei_selectsegment(self, x, y): ...

    @abstractmethod
    def ei_selectarcsegment(self, x, y): ...

    @abstractmethod
    def ei_setsegmentprop(self, propname, elementsize, automesh, hide, group): ...

    @abstractmethod
    def ei_setarcsegmentprop(self, propname, elementsize, hide, group): ...

    @abstractmethod
    def ei_clearselected(self): ...

    @abstractmethod
    def ei_addblocklabel(self, x, y): ...

    @abstractmethod
    def ei_selectlabel(self, x, y): ...

    @abstractmethod
    def ei_setblockprop(self, blockname, automesh, meshsize, group): ...

    @abstractmethod
    def ei_zoomnatural(self): ...

    def comment(self, text):
        """Add a comment. No-op for COM backend."""

    def blank_line(self):
        """Add a blank line. No-op for COM backend."""


# ------------------------------------------------------------------
# COM backend (pyfemm)
# ------------------------------------------------------------------
class ComBackend(FEMMBackend):
    """Executes FEMM commands via pyfemm COM automation."""

    def __init__(self):
        import femm as _femm
        self._femm = _femm

    def newdocument(self, doctype):
        self._femm.newdocument(doctype)

    def ei_probdef(self, units, prob_type, precision, depth, min_angle):
        self._femm.ei_probdef(units, prob_type, precision, depth, min_angle)

    def ei_addmaterial(self, name, ex, ey, qv):
        self._femm.ei_addmaterial(name, ex, ey, qv)

    def ei_addboundprop(self, name, vs, qs, c0, c1, fmt):
        self._femm.ei_addboundprop(name, vs, qs, c0, c1, fmt)

    def ei_addnode(self, x, y):
        self._femm.ei_addnode(x, y)

    def ei_addsegment(self, x1, y1, x2, y2):
        self._femm.ei_addsegment(x1, y1, x2, y2)

    def ei_addarc(self, x1, y1, x2, y2, angle, maxseg):
        self._femm.ei_addarc(x1, y1, x2, y2, angle, maxseg)

    def ei_selectsegment(self, x, y):
        self._femm.ei_selectsegment(x, y)

    def ei_selectarcsegment(self, x, y):
        self._femm.ei_selectarcsegment(x, y)

    def ei_setsegmentprop(self, propname, elementsize, automesh, hide, group):
        self._femm.ei_setsegmentprop(propname, elementsize, automesh, hide, group, "<None>")

    def ei_setarcsegmentprop(self, propname, elementsize, hide, group):
        self._femm.ei_setarcsegmentprop(propname, elementsize, hide, group, "<None>")

    def ei_clearselected(self):
        self._femm.ei_clearselected()

    def ei_addblocklabel(self, x, y):
        self._femm.ei_addblocklabel(x, y)

    def ei_selectlabel(self, x, y):
        self._femm.ei_selectlabel(x, y)

    def ei_setblockprop(self, blockname, automesh, meshsize, group):
        self._femm.ei_setblockprop(blockname, automesh, meshsize, group)

    def ei_zoomnatural(self):
        self._femm.ei_zoomnatural()


# ------------------------------------------------------------------
# Lua backend (script generation)
# ------------------------------------------------------------------
class LuaBackend(FEMMBackend):
    """Collects FEMM commands as Lua script lines."""

    def __init__(self):
        self.lines = []

    def newdocument(self, doctype):
        self.lines.append(f"newdocument({doctype})")

    def ei_probdef(self, units, prob_type, precision, depth, min_angle):
        self.lines.append(
            f'ei_probdef("{units}", "{prob_type}", {precision}, {depth}, {min_angle})')

    def ei_addmaterial(self, name, ex, ey, qv):
        self.lines.append(f'ei_addmaterial("{name}", {ex}, {ey}, {qv})')

    def ei_addboundprop(self, name, vs, qs, c0, c1, fmt):
        self.lines.append(
            f'ei_addboundprop("{name}", {vs}, {qs}, {c0}, {c1}, {fmt})')

    def ei_addnode(self, x, y):
        self.lines.append(f"ei_addnode({x:.6f}, {y:.6f})")

    def ei_addsegment(self, x1, y1, x2, y2):
        self.lines.append(
            f"ei_addsegment({x1:.6f}, {y1:.6f}, {x2:.6f}, {y2:.6f})")

    def ei_addarc(self, x1, y1, x2, y2, angle, maxseg):
        self.lines.append(
            f"ei_addarc({x1:.6f}, {y1:.6f}, {x2:.6f}, {y2:.6f}, {angle:.2f}, {maxseg})")

    def ei_selectsegment(self, x, y):
        self.lines.append(f"ei_selectsegment({x:.6f}, {y:.6f})")

    def ei_selectarcsegment(self, x, y):
        self.lines.append(f"ei_selectarcsegment({x:.6f}, {y:.6f})")

    def ei_setsegmentprop(self, propname, elementsize, automesh, hide, group):
        self.lines.append(
            f'ei_setsegmentprop("{propname}", {elementsize}, {automesh}, {hide}, {group})')

    def ei_setarcsegmentprop(self, propname, elementsize, hide, group):
        self.lines.append(
            f'ei_setarcsegmentprop("{propname}", {elementsize}, {hide}, {group})')

    def ei_clearselected(self):
        self.lines.append("ei_clearselected()")

    def ei_addblocklabel(self, x, y):
        self.lines.append(f"ei_addblocklabel({x:.6f}, {y:.6f})")

    def ei_selectlabel(self, x, y):
        self.lines.append(f"ei_selectlabel({x:.6f}, {y:.6f})")

    def ei_setblockprop(self, blockname, automesh, meshsize, group):
        self.lines.append(
            f'ei_setblockprop("{blockname}", {automesh}, {meshsize}, {group})')

    def ei_zoomnatural(self):
        self.lines.append("ei_zoomnatural()")

    def comment(self, text):
        self.lines.append(f"-- {text}")

    def blank_line(self):
        self.lines.append("")


# ------------------------------------------------------------------
# Shared model builder
# ------------------------------------------------------------------
class FEMMModelBuilder:
    """Builds a FEMM electrostatic model using a pluggable backend."""

    def __init__(self, backend: FEMMBackend):
        self.backend = backend

    def build(self, curves, config):
        """Build the complete FEMM model."""
        self._setup_problem(config)
        self._add_materials(config)
        self._add_boundaries(config)
        self._add_electrodes(curves, config)
        self._add_outer_box(curves, config)
        self._add_dielectric(curves, config)
        self._add_electrode_bodies(curves, config)
        self.backend.ei_zoomnatural()
        self.backend.blank_line()

    def _setup_problem(self, config):
        self.backend.comment("Problem definition")
        self.backend.newdocument(1)
        self.backend.ei_probdef(
            config.get("units", "millimeters"),
            config.get("problem_type", "planar"),
            1e-8,
            config.get("depth", 1.0),
            30,
        )
        self.backend.blank_line()

    def _add_materials(self, config):
        eps = config.get("permittivity", 1.0)
        self.backend.comment("Materials")
        self.backend.ei_addmaterial("Dielectric", eps, eps, 0)
        self.backend.blank_line()

    def _add_boundaries(self, config):
        self.backend.comment("Boundary conditions")
        self.backend.ei_addboundprop(
            "TopElectrode", config.get("voltage_top", 1000), 0, 0, 0, 0)
        self.backend.ei_addboundprop(
            "BotElectrode", config.get("voltage_bottom", 0), 0, 0, 0, 0)
        self.backend.ei_addboundprop("Outer", 0, 0, 0, 0, 1)
        self.backend.blank_line()

    def _add_electrodes(self, curves, config):
        is_axi = config.get("problem_type") == "axi"
        mesh = config.get("mesh_size", 0)
        automesh = 1 if mesh == 0 else 0

        self.backend.comment("Electrode geometry")

        for cx, cy, label in curves:
            pts = list(zip(cx, cy))
            self.backend.comment(label)

            boundary = "BotElectrode" if "Bot" in label else "TopElectrode"
            group = 2 if "Bot" in label else 1

            for x, y in pts:
                self.backend.ei_addnode(x, y)

            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                if abs(x2 - x1) < 1e-10 and abs(y2 - y1) < 1e-10:
                    continue
                self.backend.ei_addsegment(x1, y1, x2, y2)
                # In axi mode, segments on the axis (r=0) are purely
                # geometric closure — no voltage boundary assigned.
                if not (is_axi and abs(x1) < 1e-10 and abs(x2) < 1e-10):
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    self.backend.ei_selectsegment(mx, my)
                    self.backend.ei_setsegmentprop(boundary, mesh, automesh, 0, group)
                    self.backend.ei_clearselected()

        self.backend.blank_line()

    def _add_outer_box(self, curves, config):
        is_axi = config.get("problem_type") == "axi"
        mesh = config.get("mesh_size", 0)
        automesh = 1 if mesh == 0 else 0

        xs = [x for cx, _, _ in curves for x in cx]
        ys = [y for _, cy, _ in curves for y in cy]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        pad = span * 0.5

        bx0 = 0 if is_axi else min(xs) - pad
        bx1 = max(xs) + pad
        by0 = min(ys) - pad
        by1 = max(ys) + pad
        corners = [(bx0, by0), (bx1, by0), (bx1, by1), (bx0, by1)]

        self.backend.comment("Outer boundary")
        for x, y in corners:
            self.backend.ei_addnode(x, y)

        for i in range(4):
            x1, y1 = corners[i]
            x2, y2 = corners[(i + 1) % 4]
            if is_axi and abs(x1) < 1e-10 and abs(x2) < 1e-10:
                # Axis edge: create individual segments between
                # consecutive axis nodes so every region is closed.
                axis_ys = set()
                for cx_c, cy_c, _ in curves:
                    for xv, yv in zip(cx_c, cy_c):
                        if abs(xv) < 1e-10:
                            axis_ys.add(yv)
                axis_ys.add(y1)
                axis_ys.add(y2)
                sorted_ys = sorted(axis_ys, reverse=True)
                for j in range(len(sorted_ys) - 1):
                    self.backend.ei_addsegment(
                        0, sorted_ys[j], 0, sorted_ys[j + 1])
                continue
            self.backend.ei_addsegment(x1, y1, x2, y2)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self.backend.ei_selectsegment(mx, my)
            self.backend.ei_setsegmentprop("Outer", mesh, automesh, 0, 3)
            self.backend.ei_clearselected()

        self.backend.blank_line()

    def _add_dielectric(self, curves, config):
        mesh = config.get("mesh_size", 0)
        automesh = 1 if mesh == 0 else 0
        is_axi = config.get("problem_type") == "axi"

        if is_axi:
            lx = max(x for cx, _, _ in curves for x in cx) * 0.25
        else:
            lx = 0

        self.backend.comment("Dielectric region")
        self.backend.ei_addblocklabel(lx, 0)
        self.backend.ei_selectlabel(lx, 0)
        self.backend.ei_setblockprop("Dielectric", automesh, mesh, 0)
        self.backend.ei_clearselected()
        self.backend.blank_line()

    def _add_electrode_bodies(self, curves, config):
        """Place block labels inside closed electrode contours.

        The electrode interior is meshed with the dielectric material.
        Because the surface carries a fixed-voltage boundary, the solver
        naturally produces V = const, E = 0 inside — physically correct
        without needing the problematic ``<No Mesh>`` region.
        """
        has_cap = any(label == "Top-Cap" for _, _, label in curves)
        if not has_cap:
            return

        mesh = config.get("mesh_size", 0)
        automesh = 1 if mesh == 0 else 0
        is_axi = config.get("problem_type") == "axi"

        # Find the y-extent of the top electrode to place the label
        # safely inside the closed contour (midway between plate and cap peak).
        top_ys = [y for _, cy, label in curves
                  if "Top" in label for y in cy]
        y_mid = (min(top_ys) + max(top_ys)) / 2
        lx = max(x for cx, _, _ in curves for x in cx) * 0.25 if is_axi else 0

        self.backend.comment("Electrode bodies")
        self.backend.ei_addblocklabel(lx, y_mid)
        self.backend.ei_selectlabel(lx, y_mid)
        self.backend.ei_setblockprop("Dielectric", automesh, mesh, 1)
        self.backend.ei_clearselected()

        self.backend.ei_addblocklabel(lx, -y_mid)
        self.backend.ei_selectlabel(lx, -y_mid)
        self.backend.ei_setblockprop("Dielectric", automesh, mesh, 2)
        self.backend.ei_clearselected()
        self.backend.blank_line()
