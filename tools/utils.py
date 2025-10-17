# ============================================================
# 🧱 تحميل ملفات BREP
# ============================================================


# ============================================================
# 🧱 تحميل ملفات BREP (مرن لإصدارات pythonocc المختلفة)
# ============================================================
from pathlib import Path
from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.BRep import BRep_Builder

# نحاول العثور على دالة القراءة بصيغتين: breptools_Read أو BRepTools.Read
_read_brep_func = None
try:
    # بعض الإصدارات توفّر دالة حرة باسم breptools_Read
    from OCC.Core.BRepTools import breptools_Read as _read_brep_func  # type: ignore
except Exception:
    try:
        # وبعضها يوفّرها كـ static method ضمن BRepTools
        from OCC.Core.BRepTools import BRepTools  # type: ignore

        def _read_brep_func(shape, filename, builder):
            # قد تُعيد bool أو None حسب البايندينغ؛ نعتمد على IsNull للتحقق لاحقًا
            return BRepTools.Read(shape, filename, builder)
    except Exception:
        _read_brep_func = None


def load_brep_file(path: Path) -> TopoDS_Shape:
    """
    تحميل ملف .brep إلى TopoDS_Shape بطريقة متوافقة مع pythonocc 7.9 وما شابه.
    يرفع استثناءات واضحة إذا فشل.
    """
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"BREP file not found: {path}")

    if _read_brep_func is None:
        raise ImportError(
            "Cannot find BREP read function in this pythonocc build "
            "(neither BRepTools.Read nor breptools_Read is available)."
        )

    builder = BRep_Builder()
    shape = TopoDS_Shape()

    # استدعاء الدالة المناسبة (حسب ما وُجد أعلاه)
    _read_brep_func(shape, str(path), builder)

    # التحقق النهائي
    if shape.IsNull():
        raise RuntimeError(f"Failed to read BREP shape from: {path}")

    return shape
