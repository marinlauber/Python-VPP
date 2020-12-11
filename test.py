# import matplotlib.pyplot as plt
# import numpy as np
# from matplotlib.figure import Figure
# from matplotlib.axes._axes import Axes
# from matplotlib.axes._subplots import SubplotBase

# class MyFigure(Figure):
#     def __init__(self, *args, **kwargs):
#         """
#         custom kwarg figtitle is a figure title
#         """
#         super().__init__(*args, **kwargs)
    
#     def plot_vpp(self, data):
#         ax = self.gca()
#         ax.plot(data, label="My Label")
#         ax.legend()


# fig = plt.figure(FigureClass=MyFigure)
# fig.plot_vpp([1, 2, 3])
# plt.show()

# tws_range=np.arange(2.0,22.0,2.0),
# twa_range=np.linspace(30.0,180.0,34)

import numpy as np

from src.YachtMod import Yacht, Keel, Rudder
from src.SailMod import Main, Jib, Kite
from src.VPPMod import VPP
from src.UtilsMod import VPPResults

res = VPPResults('results')
res.polar(n=1, save=False)
res.SailChart()
