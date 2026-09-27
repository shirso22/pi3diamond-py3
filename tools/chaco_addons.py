# Enthought library imports
# PY3-PORT: was `from exceptions import IOError`. The `exceptions`
# module is gone in Python 3; these are builtins.

# PY3-PORT: BaseTool moved from chaco.api to enable.api in Chaco 4.
from enable.api import BaseTool
from traits.api import Tuple, Array


class ChacoSaveMixin:
    """
    Provides a 'save' method, that saves the enable component as graphics file.
    """

    def save_raster(self, filename):
        """
        Saves an image of a chaco component (e.g. 'Plot' or 'Container')
        to a raster file, such as .jpg or .png. The file type is terermined
        by the extension.
        """
        from chaco.api import PlotGraphicsContext
        gc = PlotGraphicsContext(self.outer_bounds, dpi=72)
        self.draw(gc, mode="normal")
        # gc.render_component(self)
        gc.save(filename)
        return

    def save_pdf(self, filename):
        """
        Saves an image of a chaco component (e.g. 'Plot' or 'Container')
        to a .pdf file.
        """
        from chaco.pdf_graphics_context import PdfPlotGraphicsContext
        gc = PdfPlotGraphicsContext(filename=filename)
        # pagesize = self.pagesize,
        # dest_box = self.dest_box,
        # dest_box_units = self.dest_box_units)
        gc.render_component(self)
        gc.save()

    def save(self, filename):
        """
        Saves the plot to a graphics file, e.g. .png or .pdf.
        
        Example of usage:
        
            plot = my_instance.line_plot
            filename = 'foo.png'
            save_figure(plot, filename)
        """
        if filename:
            if os.path.splitext(filename)[-1] == ".pdf":
                self.save_pdf(filename)
            else:
                self.save_raster(filename)
        else:
            raise IOError('Empty filename.')


from chaco.api import Plot, HPlotContainer


class SavePlot(Plot, ChacoSaveMixin):
    pass


class SaveHPlotContainer(HPlotContainer, ChacoSaveMixin):
    pass


class ClickTool(BaseTool):
    click_coords = Array

    def normal_mouse_move(self, event):
        self.click_coords = self.component.map_data((event.x, event.y))


# Major library imports
import os.path

# Enthought library imports
from enable.api import BaseTool

from .utility import save_file


class SaveTool(BaseTool):
    """
    This tool allows the user to press Ctrl+S to save a snapshot image of
    the plot component.
    """
    # -------------------------------------------------------------------------
    # Override default trait values inherited from BaseTool
    # -------------------------------------------------------------------------

    # This tool does not have a visual representation (overrides BaseTool).
    draw_mode = "none"

    # This tool is not visible (overrides BaseTool).
    visible = False

    def normal_key_pressed(self, event):
        """ Handles a key-press when the tool is in the 'normal' state.

        Saves an image of the plot if the keys pressed are Control and S.
        """
        if self.component is None:
            return

        if event.character == "s" and event.control_down:
            filename = save_file(title='Save plot as png or pdf.')
            if filename:
                self.component.save(filename)
            event.handled = True
        return


# PY3-PORT: Chaco 4 renamed SimpleZoom to ZoomTool and rebuilt the zoom
# machinery around it. The old AspectZoomTool._do_zoom below was a verbatim
# copy of Chaco 3's SimpleZoom._do_zoom with two extra lines bolted on, and it
# called internals (_get_mapper, _orig_low_setting) that no longer exist. Its
# _do_zoom signature also changed: it now takes (index_factor, value_factor).
#
# Rewritten to do only what the subclass was ever actually FOR -- lock the
# container's aspect ratio to the visible data range and publish the box --
# and to delegate the zoom itself to the modern base class.
#
# >>> This is the one piece of real API drift in the port. It is used only by
# >>> measurements/confocal_focus.py. Exercise the confocal scan zoom before
# >>> you trust it; the behaviour is reasoned, not observed.
from chaco.tools.api import ZoomTool


class AspectZoomTool(ZoomTool):
    box = Tuple()

    def _sync_aspect(self):
        component = self.component
        if component is None or component.container is None:
            return
        x_range = component.x_mapper.range
        y_range = component.y_mapper.range
        height = y_range.high - y_range.low
        if height:
            component.container.aspect_ratio = (x_range.high - x_range.low) / height
        self.box = (x_range.low, y_range.low, x_range.high, y_range.high)
        component.request_redraw()

    def _do_zoom(self, *args, **kwargs):
        result = super(AspectZoomTool, self)._do_zoom(*args, **kwargs)
        self._sync_aspect()
        return result

    def _end_select(self, event):
        result = super(AspectZoomTool, self)._end_select(event)
        self._sync_aspect()
        return result
