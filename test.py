from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core import BRepTools

print("🧪 إنشاء شكل Box...")
shape = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
print("✅ Box جاهز")

print("💾 تجربة الحفظ باستخدام BRepTools.breptools_Write...")
BRepTools.breptools_Write(shape, "test_box.brep")
print("✅ تم الحفظ بدون كراش")
