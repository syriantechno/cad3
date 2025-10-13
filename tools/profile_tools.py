
from pathlib import Path
import shutil
from typing import Optional, Tuple

# يعتمد على دالتك الحالية:
# from dxf_tools import load_dxf_file
# سنؤجل الاستيراد حتى وقت التنفيذ لتجنب كسر التشغيل في بيئات لا تحتوي على ezdxf/OCC
def _load_shape_via_dxf(file_path: str):
    from dxf_tools import load_dxf_file  # noqa: WPS433
    return load_dxf_file(file_path)

# pythonOCC imports تتم فقط عند الحاجة
def _write_brep(shape, brep_path: Path) -> None:
    from OCC.Core.BRepTools import breptools
    breptools.Write(shape, str(brep_path))

def _dump_display_png(display, shp, img_path: Path) -> None:
    # يتوقع display كائن OCC viewer (مثل qtViewer3d._display)
    display.EraseAll()
    display.DisplayShape(shp, update=True)
    try:
        display.FitAll()
    except Exception:
        pass
    # pythonocc >= 7.6: display.View.Dump
    display.View.Dump(str(img_path))

def slugify(name: str) -> str:
    s = "".join(c if c.isalnum() or c in "-_." else "_" for c in name.strip())
    return s.strip("_") or "profile"

PROFILES_ROOT = Path(__file__).resolve().parents[1] / "profiles"

def ensure_profile_dir(base_name: str) -> Path:
    dir_path = PROFILES_ROOT / base_name
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def process_dxf_to_assets(
    dxf_src_path: Path,
    profile_name: str,
    shape=None,
    display=None,
):
    """
    يحوّل DXF إلى ملفات صديقة للتحميل الفوري:
    - نسخ DXF
    - حفظ BREP للشكل
    - حفظ صورة PNG من العارض (إن توفر)

    returns: (dxf_path, brep_path, image_path)
    """
    base = slugify(profile_name) or slugify(dxf_src_path.stem)
    out_dir = ensure_profile_dir(base)

    # 1) انسخ DXF
    dxf_dst = out_dir / f"{base}.dxf"
    if str(dxf_src_path.resolve()) != str(dxf_dst.resolve()):
        shutil.copy2(dxf_src_path, dxf_dst)

    # 2) تجهيز الشكل
    shp = shape or _load_shape_via_dxf(str(dxf_src_path))
    if shp is None:
        raise RuntimeError("DXF parsing returned no shape.")

    # 3) حفظ BREP
    brep_path = out_dir / f"{base}.brep"
    _write_brep(shp, brep_path)

    # 4) حفظ صورة
    img_path = out_dir / f"{base}.png"
    if display is not None:
        try:
            _dump_display_png(display, shp, img_path)
        except Exception:
            img_path.touch()
    else:
        img_path.touch()

    return dxf_dst, brep_path, img_path

def load_brep_file(brep_path: Path):
    from OCC.Core.BRepTools import breptools_Read  # noqa: WPS433
    from OCC.Core.TopoDS import TopoDS_Shape  # noqa: WPS433
    from OCC.Core.BRep import BRep_Builder  # noqa: WPS433
    builder = BRep_Builder()
    shape = TopoDS_Shape()
    ok = breptools_Read(shape, str(brep_path), builder)
    if not ok:
        raise RuntimeError(f"Failed to read BREP: {brep_path}")
    return shape
