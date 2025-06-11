# svg-to-gcode
This is a svg-to-gcode script for the bambulab A1 printer.

The goal of this converter is to create a gcode witch you can use to draw a picture with your 3D printer.

I added a lot of options you can edit yoursel easily.
If you open the converter.py you can see a few options at the top including those:
samples_per_curve = 100
z_up = 10.0 (z_up is the up position, in witch the pencil wont write)
z_down = 5.0 (z_down is the down position, which the pencil will draw a line)
draw_feedrate = 1500 (the speed which is used to draw in mm/min)
move_feedrate = 3000 (the speed which is used to change the position in mm/min)
bed_size = 256 (most important the bed size of your printer. If you pick it too big you will eventually encounter issues)

If you start the converter, it will ask you about your svg picture.
You need to enter the path to your svg for example C:/path/to/picture.svg
