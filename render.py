"""Shaded previews of out/*.stl -> renders/*.png (VTK, offscreen)"""
import os
import sys

import vtk

COLORS = dict(body=(0.36, 0.66, 0.68), figure=(0.95, 0.62, 0.25),
              sponge_insert=(0.93, 0.93, 0.93), soap_insert=(0.93, 0.93, 0.93), brush_insert=(0.93, 0.93, 0.93),
              phantom_sponge=(0.96, 0.82, 0.26), phantom_soap=(0.3, 0.3, 0.32), phantom_brush=(0.75, 0.22, 0.17))


def actor(name):
    r = vtk.vtkSTLReader(); r.SetFileName(f"out/{name}.stl")
    n = vtk.vtkPolyDataNormals(); n.SetInputConnection(r.GetOutputPort()); n.SetFeatureAngle(35)
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(n.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m)
    pr = a.GetProperty(); pr.SetColor(*COLORS[name]); pr.SetSpecular(0.15); pr.SetSpecularPower(20)
    if name.startswith("phantom"):
        pr.SetOpacity(0.45)
    return a


def render(names, fname, pos, focal=None, zoom=1.0):
    ren = vtk.vtkRenderer(); ren.SetBackground(1, 1, 1); ren.SetUseDepthPeeling(True)
    for n in names:
        if os.path.exists(f"out/{n}.stl"):
            ren.AddActor(actor(n))
    win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.AddRenderer(ren)
    win.SetSize(1200, 900); win.SetAlphaBitPlanes(1); win.SetMultiSamples(8)
    cam = ren.GetActiveCamera()
    ren.ResetCamera()
    if focal is None:
        focal = cam.GetFocalPoint()
    cam.SetFocalPoint(*focal); cam.SetPosition(*pos); cam.SetViewUp(0, 0, 1)
    ren.ResetCamera() if focal is None else None
    ren.ResetCameraClippingRange(); cam.Zoom(zoom)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(f"renders/{fname}.png"); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    print("rendered", fname)


if __name__ == "__main__":
    os.makedirs("renders", exist_ok=True)
    parts = ["body", "figure", "sponge_insert", "soap_insert", "brush_insert"]
    ph = ["phantom_sponge", "phantom_soap", "phantom_brush"]
    c = (93, 50, 45)
    render(parts + ph, "1_loaded", (-150, -420, 330), c, 1.0)
    render(parts, "2_empty", (-100, -400, 380), c, 1.15)
    render(["body", "figure"], "3_drain_pan", (93, -120, 520), (93, 50, 20), 1.3)
    render(["body", "figure"], "4_figure", (60, -190, 90), (156, 0, 35), 1.0)
    render(["body", "figure", "sponge_insert"], "6_chair", (40, -170, 190), (130, 25, 40), 0.9)
    render(["body", "figure", "sponge_insert"], "5_figure_side", (420, -10, 45), (156, 0, 30), 1.6)
