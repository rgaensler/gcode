from printing.GRedirect import RedirectionTargets
from printing.PrinterComponent import PrinterComponent


class Heater(PrinterComponent):
    redirector = RedirectionTargets.HEATERS

    def handle_gcode(self, *args):
        pass

    def boot(self):
        pass

    def shutdown(self):
        pass