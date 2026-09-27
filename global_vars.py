"""
This is a module used to share the globally used variables among the single modules.
Since there is only a single instance of this module alive changes made to the variables are
reflected everywhere.
See: https://docs.python.org/2/faq/programming.html#how-do-i-share-global-variables-across-modules
Each module that wants to make use of these global variables must import it!
"""

win_low = 590
win_high = 790
ref_low = 1500
ref_high = 1700
pixel_count = 0
line_count = 0
# Nv spin manipulation variables
mw_frequency = 2.7e9
mw_power = -10.
mw_x_t_pi2 = 50.
mw_x_t_pi = 100.
mw_x_t_3pi2 = 150.
mw_y_t_pi2 = 50.
mw_y_t_pi = 100.
mw_y_t_3pi2 = 150.
