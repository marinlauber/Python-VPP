from src.UtilsMod import VPPResults

results_1 = VPPResults("results_1_filename")
results_2 = VPPResults("results_2_filename")
results_1.polar_comp(results_2, n=3, save=True)
