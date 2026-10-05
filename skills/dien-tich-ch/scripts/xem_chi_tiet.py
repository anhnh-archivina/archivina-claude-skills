#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ve anh phong to mot vung cua DXF de xem net ranh (di sau vao block/xref), dung khi can chan doan cho ho.

    python xem_chi_tiet.py <file.dxf> <anh.png> x0 y0 x1 y1
Mau: do dam = A-Vua trat, xanh la = A-Wall, vang = A-Column, tim = A-Line, xanh duong = A-Door, cyan = A-Glaz.
Cham tron = dinh cua net ranh (cac dau mut/goc ma cua de nhin cho ho).
"""
import importlib.util
import os
import sys

import ezdxf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from ezdxf import path as ezpath

here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("tpp", os.path.join(here, "tao_polyline_phong.py"))
tpp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tpp)

dxf, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = [float(v) for v in sys.argv[3:7]]
doc = ezdxf.readfile(dxf)
colors = {"a-vua trat": "#8b0000", "a-wall": "#2b8a3e", "a-column": "#d4a000", "a-line": "#7048e8",
          "a-door": "#1c7ed6", "a-glaz": "#15aabf"}
fig = plt.figure(figsize=(13, 13), dpi=90)
ax = fig.add_axes([0.03, 0.03, 0.95, 0.95])
for e in tpp.walk(doc.modelspace()):
    lay = tpp.layer_goc(e.dxf.layer)
    if lay not in colors or e.dxftype() not in ("LINE", "LWPOLYLINE", "ARC"):
        continue
    try:
        if e.dxftype() == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        else:
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(2)]
            if e.dxftype() == "LWPOLYLINE" and e.closed:
                pts.append(pts[0])
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=colors[lay], lw=1.4)
        if lay in ("a-vua trat", "a-wall", "a-column", "a-line"):
            ax.plot(xs, ys, "o", ms=2.5, color=colors[lay])
    except Exception:
        pass
ax.set_xlim(x0, x1)
ax.set_ylim(y0, y1)
ax.set_aspect("equal")
ax.grid(True, lw=0.3)
fig.savefig(out)
print("ok")
