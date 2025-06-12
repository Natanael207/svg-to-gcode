from svgpathtools import svg2paths2, wsvg, Path
from pathlib import Path as SysPath
import sys

samples_per_curve = 25
z_up = 10.0
z_down = 5.0
draw_feedrate = 1500
move_feedrate = 3000

bed_size = 256

RED = "\033[91m"
RESET = "\033[0m"

def distance(p1, p2):
    return abs(p1 - p2)

def get_svg_bounds(paths):
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for path in paths:
        for segment in path:
            pts = [segment.start, segment.end]
            if hasattr(segment, 'control1'):
                pts.append(segment.control1)
            if hasattr(segment, 'control2'):
                pts.append(segment.control2)

            for p in pts:
                x, y = p.real, p.imag
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    width = max_x - min_x
    height = max_y - min_y
    return min_x, min_y, max_x, max_y, width, height

def split_paths_on_gaps(paths, attributes, gap_threshold):
    new_paths = []
    new_attributes = []

    for path, attr in zip(paths, attributes):
        current_subpath = []
        prev_segment = None

        for segment in path:
            if prev_segment is None:
                current_subpath.append(segment)
            else:
                dist = distance(prev_segment.end, segment.start)
                if dist > gap_threshold:
                    new_paths.append(Path(*current_subpath))
                    new_attributes.append(attr.copy())
                    current_subpath = [segment]
                else:
                    current_subpath.append(segment)
            prev_segment = segment

        if current_subpath:
            new_paths.append(Path(*current_subpath))
            new_attributes.append(attr.copy())

    return new_paths, new_attributes

def convert_svg_to_gcode(paths, scale, min_x, min_y, x_offset, y_offset, output_file, min_feature_size):
    gcode = [
        "; G-code zum Zeichnen mit Bambu Lab A1",
        "G21 ; mm",
        "G90 ; absolut",
        "G28 ; home"
    ]

    ignored_paths = 0
    pen_lifts = 0
    gcode_min_x = gcode_min_y = float('inf')
    gcode_max_x = gcode_max_y = float('-inf')

    for path in paths:
        path_min_x = path_min_y = float('inf')
        path_max_x = path_max_y = float('-inf')

        for segment in path:
            pts = [segment.start, segment.end]
            if hasattr(segment, 'control1'):
                pts.append(segment.control1)
            if hasattr(segment, 'control2'):
                pts.append(segment.control2)

            for p in pts:
                x = (p.real - min_x) * scale
                y = (p.imag - min_y) * scale
                path_min_x = min(path_min_x, x)
                path_max_x = max(path_max_x, x)
                path_min_y = min(path_min_y, y)
                path_max_y = max(path_max_y, y)

        if (path_max_x - path_min_x < min_feature_size) and (path_max_y - path_min_y < min_feature_size):
            ignored_paths += 1
            continue

        points = []
        for segment in path:
            for i in range(samples_per_curve + 1):
                t = i / samples_per_curve
                point = segment.point(t)
                shifted_x = (point.real - min_x) * scale + x_offset
                shifted_y = (point.imag - min_y) * scale + y_offset
                points.append(complex(shifted_x, shifted_y))

        if not points:
            continue

        start = points[0]
        gcode.append(f"G1 Z{z_up:.2f} F{move_feedrate}")
        gcode.append(f"G0 X{start.real:.2f} Y{start.imag:.2f} F{move_feedrate}")
        gcode.append(f"G1 Z{z_down:.2f} F{move_feedrate}")
        pen_lifts += 1

        for pt in points[1:]:
            gcode.append(f"G1 X{pt.real:.2f} Y{pt.imag:.2f} F{draw_feedrate}")

        gcode.append(f"G1 Z{z_up:.2f} F{move_feedrate}")

        for pt in points:
            gcode_min_x = min(gcode_min_x, pt.real)
            gcode_max_x = max(gcode_max_x, pt.real)
            gcode_min_y = min(gcode_min_y, pt.imag)
            gcode_max_y = max(gcode_max_y, pt.imag)

    gcode += [
        "G1 Z10 ; Stift ganz hoch",
        "G28 ; zurück Home",
        "M84 ; Motoren aus"
    ]

    with open(output_file, 'w') as f:
        f.write('\n'.join(gcode))

    print(f"✂️ Pfadwechsel (Stift hoch): {pen_lifts}")
    print(f"ℹ️ Ignorierte kleine Objekte: {ignored_paths}")
    return gcode_min_x, gcode_max_x, gcode_min_y, gcode_max_y

if __name__ == "__main__":
    print("🧩 SVG Split + ✏️ G-code Generator")

    svg_path = input("📂 Pfad zur SVG-Datei: ").strip().strip('"')
    if not SysPath(svg_path).exists():
        print("❌ Datei nicht gefunden.")
        sys.exit(1)

    gcode_name = input("💾 G-code-Dateiname (ohne .gcode): ").strip()
    if not gcode_name:
        print("❌ Kein gültiger Name.")
        sys.exit(1)

    try:
        desired_width = float(input(f"📏 Gewünschte Breite (max {bed_size} mm): ").strip())
        if not (0 < desired_width <= bed_size):
            raise ValueError()
    except ValueError:
        print(f"❌ Ungültige Eingabe. Breite muss zwischen 0 und {bed_size} mm sein.")
        sys.exit(1)

    try:
        gap_threshold = float(input("🔍 Abstandsschwelle für Pfad-Trennung (z. B. 5.0): ").strip())
    except ValueError:
        print("❌ Ungültiger Abstand.")
        sys.exit(1)

    try:
        min_feature_size = float(input("🔎 Minimale Feature-Größe in mm (z. B. 0.5): ").strip())
    except ValueError:
        print("❌ Ungültige Eingabe für minimale Feature-Größe.")
        sys.exit(1)

    paths, attributes, svg_attrs = svg2paths2(svg_path)
    split_paths, _ = split_paths_on_gaps(paths, attributes, gap_threshold)

    min_x, min_y, max_x, max_y, width, height = get_svg_bounds(split_paths)
    scale = desired_width / width
    final_width = width * scale
    final_height = height * scale
    x_offset = (bed_size - final_width) / 2
    y_offset = (bed_size - final_height) / 2

    print(f"⚖️ Skalierung: {scale:.4f}")
    print(f"🖼️ Endgröße: {final_width:.2f} x {final_height:.2f} mm")
    print(f"📍 Offset: X={x_offset:.2f}, Y={y_offset:.2f}")

    output_path = SysPath(svg_path).parent / f"{gcode_name}.gcode"
    min_xx, max_xx, min_yy, max_yy = convert_svg_to_gcode(
        split_paths, scale, min_x, min_y, x_offset, y_offset, output_path, min_feature_size
    )

    if min_xx < 0 or max_xx > bed_size:
        print(f"{RED}❌ X-Koordinaten außerhalb des Druckbereichs!{RESET}")
    if min_yy < 0 or max_yy > bed_size:
        print(f"{RED}❌ Y-Koordinaten außerhalb des Druckbereichs!{RESET}")
    if min_xx >= 0 and max_xx <= bed_size and min_yy >= 0 and max_yy <= bed_size:
        print("✅ Alle Koordinaten innerhalb des Druckbereichs.")

    input("\n⏹️  Drücke Enter zum Beenden...")
