from svgpathtools import svg2paths2
from pathlib import Path

samples_per_curve = 100
z_up = 10.0
z_down = 5.0
draw_feedrate = 1500
move_feedrate = 3000

bed_size = 256  # Print bed size (mm)

# ANSI escape code for red font
RED = "\033[91m"
RESET = "\033[0m"

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
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y

    width = max_x - min_x
    height = max_y - min_y
    return min_x, min_y, max_x, max_y, width, height

def convert_svg_to_plotter_gcode(svg_file, output_file, scale, min_x, min_y, x_offset, y_offset):
    paths, _, _ = svg2paths2(svg_file)

    gcode = []
    gcode.append("; G-code for drawing with Bambu Lab A1")
    gcode.append("G21 ; mm")
    gcode.append("G90 ; absolut")
    gcode.append("G28 ; home")

    # Track variables for Min/Max in G-Code coordinates
    gcode_min_x = float('inf')
    gcode_min_y = float('inf')
    gcode_max_x = float('-inf')
    gcode_max_y = float('-inf')

    for path in paths:
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

        for pt in points[1:]:
            gcode.append(f"G1 X{pt.real:.2f} Y{pt.imag:.2f} F{draw_feedrate}")

        gcode.append(f"G1 Z{z_up:.2f} F{move_feedrate}")

        # Update min/max
        for pt in points:
            if pt.real < gcode_min_x:
                gcode_min_x = pt.real
            if pt.real > gcode_max_x:
                gcode_max_x = pt.real
            if pt.imag < gcode_min_y:
                gcode_min_y = pt.imag
            if pt.imag > gcode_max_y:
                gcode_max_y = pt.imag

    gcode += [
        "G1 Z10 ; Pen all the way up",
        "G28 ; back Home",
        "M84 ; Motors off"
    ]

    with open(output_file, 'w') as f:
        f.write('\n'.join(gcode))

    return gcode_min_x, gcode_max_x, gcode_min_y, gcode_max_y

if __name__ == "__main__":
    print("✏️ SVG to G-code (Drawing with Bambu Lab A1)")

    svg_path = input("📂 Enter the path to the SVG file: ").strip().strip('"')
    if not Path(svg_path).exists():
        print("❌ File not found.")
        exit(1)

    gcode_name = input("💾 G-code-file name (without .gcode): ").strip()
    if not gcode_name:
        print("❌ No valid Name.")
        exit(1)

    paths, _, _ = svg2paths2(svg_path)
    min_x, min_y, max_x, max_y, width, height = get_svg_bounds(paths)
    print(f"ℹ️ Original SVG Size: width {width:.2f} mm, height {height:.2f} mm")

    try:
        desired_width = float(input(f"📏 Enter the desired width of the drawing in mm (max {bed_size}): ").strip())
        if desired_width <= 0 or desired_width > bed_size:
            raise ValueError()
    except ValueError:
        print(f"❌ Invalid input. Width must be between 0 and {bed_size} mm.")
        exit(1)

    scale = desired_width / width
    final_width = width * scale
    final_height = height * scale

    x_offset = (bed_size - final_width) / 2
    y_offset = (bed_size - final_height) / 2

    print(f"⚖️ Scaling factor: {scale:.4f}")
    print(f"✅ Final size of the drawing: width {final_width:.2f} mm, height {final_height:.2f} mm")
    print(f"🖼️ Drawing is centered at X={x_offset:.2f} mm, Y={y_offset:.2f} mm")

    min_gcode_x, max_gcode_x, min_gcode_y, max_gcode_y = convert_svg_to_plotter_gcode(
        svg_path, Path(svg_path).parent / f"{gcode_name}.gcode",
        scale, min_x, min_y, x_offset, y_offset
    )

    print(f"\n📐 G-code X Area: {min_gcode_x:.2f} mm up to {max_gcode_x:.2f} mm")
    print(f"📐 G-code Y Area: {min_gcode_y:.2f} mm up to {max_gcode_y:.2f} mm")

    error = False
    if min_gcode_x < 0 or max_gcode_x > bed_size:
        print(f"{RED}❌ X-coordinates outside the print area!{RESET}")
        error = True
    if min_gcode_y < 0 or max_gcode_y > bed_size:
        print(f"{RED}❌ Y-coordinates outside the print area!{RESET}")
        error = True

    if not error:
        print("✅ All coordinates are within the print area.")
